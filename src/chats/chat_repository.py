from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ChatMessage


class ChatRepository:
    @staticmethod
    async def get_history_by_id(conn: AsyncSession, id: int):
        stmt = select(ChatMessage).where(ChatMessage.chat_id == id)
        result = await conn.execute(stmt)
        messages = result.scalars().all()

        return messages
