from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database import sessionmanager
from src.database.db_enums import MessageSender
from src.database.models import Chat, ChatMessage


class ChatRepository:
    @staticmethod
    async def create_chat(conn: AsyncSession, user_id: int, name: str):
        new_chat = Chat(user_id=user_id, name=name)
        conn.add(new_chat)
        await conn.commit()
        await conn.refresh(new_chat)
        return new_chat.id

    @staticmethod
    async def get_all(conn: AsyncSession):
        stmt = select(Chat).order_by(Chat.created_at.asc())

        result = await conn.execute(stmt)

        chats = result.scalars().all()

        return chats

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
    async def save_user_bot_exchange(
        chat_id: int, user_message: str, bot_response: str
    ):
        async with sessionmanager.session() as conn:
            conn.add(
                ChatMessage(
                    chat_id=chat_id, content=user_message, sender=MessageSender.USER
                )
            )
            conn.add(
                ChatMessage(
                    chat_id=chat_id, content=bot_response, sender=MessageSender.BOT
                )
            )
            await conn.commit()

    @staticmethod
    async def get_by_id(
        conn: AsyncSession,
        id: int,
        columns: Optional[List] = None,
        load: Optional[List] = None,
    ):
        if not columns:
            stmt = select(Chat).where(Chat.id == id)
        else:
            stmt = select(*columns).where(Chat.id == id)

        if load:
            stmt.options(*load)

        result = await conn.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_chat_messages(
        conn: AsyncSession, id: int, columns: Optional[List] = None
    ):
        if not columns:
            stmt = select(ChatMessage).where(ChatMessage.chat_id == id)
        else:
            stmt = select(*columns).where(ChatMessage.chat_id == id)

        stmt = stmt.order_by(ChatMessage.created_at.asc())

        result = await conn.execute(stmt)

        return result.scalars().all()
