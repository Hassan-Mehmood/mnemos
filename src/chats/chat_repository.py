from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Chat, ChatMessage


class ChatRepository:
    @staticmethod
    async def create_chat(conn: AsyncSession, user_id: int):
        new_chat = Chat(user_id=user_id)
        conn.add(new_chat)
        await conn.flush()
        return new_chat.id

    @staticmethod
    async def get_history_by_id(conn: AsyncSession, id: int):
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await conn.execute(stmt)
        messages = result.scalars().all()

        return messages

    @staticmethod
    async def save_message(conn: AsyncSession, chat_id: int, content: str, sender: str):
        new_message = ChatMessage(chat_id=chat_id, content=content, sender=sender)
        conn.add(new_message)
        await conn.commit()

    @staticmethod
    async def get_chat_by_id(conn: AsyncSession, id: int):
        stmt = select(ChatMessage.id).where(ChatMessage.chat_id == id)
        result = await conn.execute(stmt)
        messages = result.scalars().first()

        return messages
