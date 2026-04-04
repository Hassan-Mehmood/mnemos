import math
from datetime import datetime, timezone
from typing import List, cast
from uuid import UUID

import numpy as np
import tiktoken
from pydantic import BaseModel

from src.chats.chat_enums import ChatMessageDict
from src.chats.chat_repository import ChatRepository
from src.core.config import get_settings
from src.core.logger import logger
from src.memory.factual_memory import FactualMemory
from src.memory.long_term_memory import LongTermSemanticMemory
from src.memory.memory_gate import GateDecision, MemoryGate
from src.memory.memory_log_repository import MemoryLogRepository
from src.memory.short_term_memory import ShortTermMemory
from src.users.user_repository import UserRepository

settings = get_settings()

_tokenizer = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_tokenizer.encode(text))


class RetrievedMemory(BaseModel):
    short_term: List[ChatMessageDict]
    factual: List = []
    semantic: List[str] = []
    tokens_used: int = 0


class MemoryRetriever:
    def __init__(
        self,
        chat_repository: ChatRepository,
        user_repository: UserRepository,
        memory_log_repository: MemoryLogRepository,
    ):
        # repositories
        self.chat_repository = chat_repository
        self.user_repository = user_repository
        self.memory_log_repository = memory_log_repository

        # memory gate
        self.memory_gate = MemoryGate()

        # memory modules
        self.long_term_memory = LongTermSemanticMemory()
        self.factual_memory = FactualMemory(user_repository=self.user_repository)
        self.short_term_memory = ShortTermMemory(
            chat_repository=self.chat_repository,
            max_length=10,
        )

    async def retrieve(
        self, chat_id: UUID, user_id: UUID, message_id: UUID, query: str
    ) -> RetrievedMemory:

        should_fetch_memory, reason = await self.memory_gate.should_retrieve(query)
        decision = GateDecision.RETRIEVE if should_fetch_memory else GateDecision.SKIP

        logger.info(f"MemoryGate [{decision}] | reason: {reason} | query: '{query}'")

        await self.memory_log_repository.log_gate_decision(
            user_id=user_id,
            message_id=message_id,
            decision=decision,
            reason=reason,
        )

        short_term = await self.short_term_memory.prepare(chat_id=chat_id, query=query)
        all_factual = await self.factual_memory.retrieve(
            user_id=user_id, confidence_threshold=0.8
        )

        # Factual memory gets first priority in the token budget
        token_budget = settings.MEMORY_TOKEN_BUDGET
        factual = []
        for mem in all_factual:
            text = (
                f'Key: {mem.key} | Value: "{mem.value}" (confidence: {mem.confidence})'
            )
            cost = _count_tokens(text)
            if cost > token_budget:
                break
            factual.append(mem)
            token_budget -= cost

        logger.info(
            f"FactualMemory | injected {len(factual)}/{len(all_factual)} items | "
            f"tokens used: {settings.MEMORY_TOKEN_BUDGET - token_budget} | remaining budget: {token_budget}"
        )

        top_semantic = []
        if should_fetch_memory:
            document_embeddings = await self.user_repository.get_user_memory_embeddings(
                user_id=user_id
            )

            if document_embeddings:
                query_embedding = self.long_term_memory.create_embeddings(
                    [query], is_query=True
                )

                similarity = self.long_term_memory.compute_similarity(
                    query_embeddings=query_embedding,
                    document_embeddings=np.array(
                        [doc.embedding for doc in document_embeddings]
                    ),
                )

                sim_scores = similarity[0].tolist()
                now = datetime.now(timezone.utc)

                ranked = []
                for sim_score, doc in zip(sim_scores, document_embeddings):
                    importance_score = doc.memory.confidence

                    # recency: exponential decay with 30-day half-life
                    created_at = cast(datetime, doc.created_at)
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)

                    days_old = (now - created_at).total_seconds() / 86400.0
                    recency_score = math.exp(-days_old / 30.0)

                    final_score = (
                        (0.6 * sim_score)
                        + (0.3 * importance_score)
                        + (0.1 * recency_score)
                    )
                    ranked.append((final_score, sim_score, doc))

                ranked.sort(key=lambda x: x[0], reverse=True)

                top_semantic = []
                for final_score, sim_score, doc in ranked[: settings.SEMANTIC_TOP_K]:
                    if sim_score < settings.SEMANTIC_SIMILARITY_THRESHOLD:
                        continue
                    cost = _count_tokens(doc.content)
                    if cost > token_budget:
                        break
                    top_semantic.append(doc.content)
                    token_budget -= cost

                logger.info(
                    f"SemanticRetrieval | top final scores: {[round(s, 3) for s, _, _ in ranked[: settings.SEMANTIC_TOP_K]]} | kept: {len(top_semantic)} | remaining budget: {token_budget}"
                )

        return RetrievedMemory(
            short_term=short_term,
            factual=factual,
            semantic=top_semantic,
            tokens_used=settings.MEMORY_TOKEN_BUDGET - token_budget,
        )
