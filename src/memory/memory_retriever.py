import asyncio
from typing import List
from uuid import UUID

from pydantic import BaseModel

from src.chats.chat_enums import ChatMessageDict
from src.chats.chat_repository import ChatRepository
from src.logger import logger
from src.memory.factual_memory import FactualMemory
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
        self.chat_repository = chat_repository
        self.user_repository = user_repository
        self.memory_log_repository = memory_log_repository

        self.memory_gate = MemoryGate()
        self.factual_memory = FactualMemory(user_repository=self.user_repository)
        self.short_term_memory = ShortTermMemory(
            chat_repository=self.chat_repository,
            max_length=10,
        )

    async def retrieve(
        self, chat_id: UUID, user_id: UUID, message_id: UUID, query: str
    ) -> RetrievedMemory:
        should_fetch_factual, reason = await self.memory_gate.should_extract(query)
        decision = GateDecision.EXTRACT if should_fetch_factual else GateDecision.SKIP

        logger.info(f"MemoryGate [{decision}] | reason: {reason} | query: '{query}'")

        await self.memory_log_repository.log_gate_decision(
            user_id=user_id,
            message_id=message_id,
            decision=decision,
            reason=reason,
        )

        tasks: List = [self.short_term_memory.prepare(chat_id=chat_id, query=query)]
        if should_fetch_factual:
            tasks.append(self.factual_memory.prepare(user_id=user_id, query=query))

        results = await asyncio.gather(*tasks)

        return RetrievedMemory(
            short_term=results[0],
            factual=results[1] if should_fetch_factual else [],
        )
