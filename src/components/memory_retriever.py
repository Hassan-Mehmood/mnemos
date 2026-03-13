from src.chats.chat_repository import ChatRepository
from src.components.short_term_memory import ShortTermMemory
from src.logger import logger


class MemoryRetriever:
    def __init__(self, chat_repository: ChatRepository):
        self.chat_repository = chat_repository
        self.short_term_memory = ShortTermMemory(
            chat_repository=self.chat_repository,
            max_length=10,
        )
        # self.memory_store = memory_store

    async def retrieve(self, chat_id: int, query: str):

        short_term_memory = await self.short_term_memory.prepare(
            chat_id=chat_id, query=query
        )

        logger.info(
            f"Retrieved memory for chat_id {chat_id}: {len(short_term_memory)} messages"
        )

        return short_term_memory
