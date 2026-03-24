from typing import List
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemoryEmbedding, MemoryStructured
from src.schemas.memory_extractor_schema import ExtractorOutput


class UserRepository:
    def __init__(self, conn: AsyncSession):
        self.conn = conn

    async def get_memory(self, user_id: UUID, key: str):
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
        self,
        kv_memories: List[ExtractorOutput],
        embeddings: List,
        user_id: UUID,
    ) -> None:
        for memory, embedding in zip(kv_memories, embeddings):
            new_record = MemoryStructured(
                id=uuid4(),
                user_id=user_id,
                key=memory.key,
                value=memory.value,
                confidence=memory.confidence,
            )
            self.conn.add(new_record)
            await self.conn.flush()

            embedding_record = MemoryEmbedding(
                id=uuid4(),
                user_id=user_id,
                memory_id=new_record.id,
                content=f"{memory.key}: {memory.value}",
                embedding=embedding,
            )
            self.conn.add(embedding_record)

        await self.conn.commit()

    async def get_user_memories(self, user_id: UUID) -> List[ExtractorOutput]:
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
