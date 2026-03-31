from typing import List
from uuid import UUID

from pydantic import BaseModel

from src.chats.chat_enums import ChatMessageDict
from src.chats.chat_repository import ChatRepository
from src.core.logger import logger
from src.memory.factual_memory import FactualMemory
from src.memory.long_term_memory import LongTermSemanticMemory
from src.memory.memory_gate import GateDecision, MemoryGate
from src.memory.memory_log_repository import MemoryLogRepository
from src.memory.short_term_memory import ShortTermMemory
from src.users.user_repository import UserRepository


class RetrievedMemory(BaseModel):
    short_term: List[ChatMessageDict]
    factual: List = []


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
            user_id=user_id, confidence_threshold=8.0
        )

        if should_fetch_memory:
            document_embeddings = await self.user_repository.get_user_memory_embeddings(
                user_id=user_id
            )

            if document_embeddings:
                query_embedding = self.long_term_memory.create_embeddings(
                    [query], is_query=True
                )

                semantic = self.long_term_memory.compute_similarity(
                    query_embeddings=query_embedding,
                    document_embeddings=[doc.embedding for doc in document_embeddings],
                )

                print("document_embeddings:", document_embeddings)
                print("Semantic Memory:", semantic)

        return RetrievedMemory(
            short_term=short_term,
            factual=factual,
        )
