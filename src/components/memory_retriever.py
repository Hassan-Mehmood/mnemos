from uuid import UUID

from src.chats.chat_repository import ChatRepository
from src.components.factual_memory import FactualMemory
from src.components.short_term_memory import ShortTermMemory
from src.users.user_repository import UserRepository


class MemoryRetriever:
    def __init__(
        self, chat_repository: ChatRepository, user_repository: UserRepository
    ):
        self.chat_repository = chat_repository
        self.user_repository = user_repository

        self.short_term_memory = ShortTermMemory(
            chat_repository=self.chat_repository,
            max_length=10,
        )
        self.factual_memory = FactualMemory(user_repository=self.user_repository)

    async def retrieve(self, chat_id: UUID, user_id: UUID, query: str):

        short_term_memory = await self.short_term_memory.prepare(
            chat_id=chat_id, query=query
        )
        factual_memory = await self.factual_memory.prepare(user_id=user_id, query=query)

        return short_term_memory, factual_memory
