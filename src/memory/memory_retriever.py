import math
from datetime import datetime, timezone
from typing import List, cast
from uuid import UUID

import numpy as np
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


class RetrievedMemory(BaseModel):
    short_term: List[ChatMessageDict]
    factual: List = []
    semantic: List[str] = []


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
        factual = await self.factual_memory.retrieve(
            user_id=user_id, confidence_threshold=0.8
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

                top_semantic = [
                    doc.content
                    for final_score, sim_score, doc in ranked[: settings.SEMANTIC_TOP_K]
                    if sim_score >= settings.SEMANTIC_SIMILARITY_THRESHOLD
                ]

                logger.info(
                    f"SemanticRetrieval | top final scores: {[round(s, 3) for s, _, _ in ranked[: settings.SEMANTIC_TOP_K]]} | kept: {len(top_semantic)}"
                )

        return RetrievedMemory(
            short_term=short_term,
            factual=factual,
            semantic=top_semantic,
        )
