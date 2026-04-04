import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.models import MemoryLog
from src.memory.memory_gate import GateDecision


class MemoryLogRepository:
    def __init__(self, conn: AsyncSession):
        self.conn = conn

    async def log_gate_decision(
        self,
        user_id: uuid.UUID,
        message_id: uuid.UUID,
        decision: GateDecision,
        reason: str,
    ) -> None:
        log = MemoryLog(
            user_id=user_id,
            message_id=message_id,
            gate_decision=decision.value,
            gate_reason=reason,
        )
        self.conn.add(log)
        await self.conn.commit()

    async def update_token_count(
        self,
        message_id: uuid.UUID,
        token_count: int,
    ) -> None:
        result = await self.conn.execute(
            select(MemoryLog).where(MemoryLog.message_id == message_id)
        )
        log = result.scalars().first()
        if log is not None:
            log.token_count = token_count
            await self.conn.commit()
