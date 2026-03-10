from src.components.short_term_memory import ShortTermMemory
from src.database.database import AsyncSession
from src.logger import logger


class MemoryRetriever:
    def __init__(self, conn: AsyncSession):
        self.conn = conn
        self.short_term_memory = ShortTermMemory(max_length=10)
        # self.memory_store = memory_store

    async def retrieve(self, chat_id: int, query: str):

        short_term_memory = await self.short_term_memory.prepare(
            conn=self.conn,
            chat_id=chat_id,
            query=query,
        )

        logger.info(
            f"Retrieved memory for chat_id {chat_id}: {len(short_term_memory)} messages"
        )

        return short_term_memory
