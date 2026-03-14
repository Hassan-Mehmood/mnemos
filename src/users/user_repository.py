import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemoryStructured
from src.logger import logger
from src.schemas.memory_extractor_schema import ExtractorOutput


class UserRepository:
    def __init__(self, conn: AsyncSession):
        self.conn = conn

    async def get_memory(self, user_id: uuid.UUID, key: str):
        result = await self.conn.execute(
            select(MemoryStructured).where(
                MemoryStructured.user_id == user_id,
                MemoryStructured.key == key,
                MemoryStructured.superseded_by == None,
            )
        )

        memory = result.scalars().first()

        return memory

    async def save_memories(
        self, memories: List[ExtractorOutput], user_id: uuid.UUID
    ) -> None:
        for memory in memories:
            existing = await self.get_memory(user_id, memory.key)
            new_id = uuid.uuid4()

            if existing is not None:
                existing.superseded_by = new_id
                await self.conn.flush()

            new_record = MemoryStructured(
                id=new_id,
                user_id=user_id,
                key=memory.key,
                value=memory.value,
                confidence=memory.confidence,
            )
            self.conn.add(new_record)
            await self.conn.flush()

        await self.conn.commit()
