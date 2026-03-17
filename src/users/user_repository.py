import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemoryStructured
from src.schemas.memory_extractor_schema import ExtractorOutput


class UserRepository:
    def __init__(self, conn: AsyncSession):
        self.conn = conn

    async def get_memory(self, user_id: uuid.UUID, key: str):
        result = await self.conn.execute(
            select(MemoryStructured).where(
                MemoryStructured.user_id == user_id,
                MemoryStructured.key == key,
                MemoryStructured.superseded_by.is_(None),
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

    async def get_user_memories(self, user_id: uuid.UUID) -> List[ExtractorOutput]:
        result = await self.conn.execute(
            select(MemoryStructured)
            .where(
                MemoryStructured.user_id == user_id,
                MemoryStructured.superseded_by.is_(None),
            )
            .order_by(MemoryStructured.created_at.desc())
        )

        memories = result.scalars().all()

        return [
            ExtractorOutput(
                key=mem.key,
                value=mem.value,
                confidence=mem.confidence,
            )
            for mem in memories
        ]
