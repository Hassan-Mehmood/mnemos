from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database import sessionmanager
from src.database.db_enums import MessageSender
from src.database.models import Chat, ChatMessage


class ChatRepository:
    def __init__(self, conn: AsyncSession):
        self.conn = conn

    async def create_chat(self, user_id: int, name: str):
        new_chat = Chat(user_id=user_id, name=name)
        self.conn.add(new_chat)
        await self.conn.commit()
        await self.conn.refresh(new_chat)
        return new_chat.id

    async def get_all(self):
        stmt = select(Chat).order_by(Chat.created_at.asc())

        result = await self.conn.execute(stmt)

        chats = result.scalars().all()

        return chats

    async def get_history_by_id(self, id: int):
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self.conn.execute(stmt)
        messages = result.scalars().all()

        return messages

    async def save_user_bot_exchange(
        self, chat_id: int, user_message: str, bot_response: str
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

    async def get_by_id(
        self,
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

        result = await self.conn.execute(stmt)
        return result.scalars().first()

    async def get_chat_messages(self, id: int, columns: Optional[List] = None):
        if not columns:
            stmt = select(ChatMessage).where(ChatMessage.chat_id == id)
        else:
            stmt = select(*columns).where(ChatMessage.chat_id == id)

        stmt = stmt.order_by(ChatMessage.created_at.asc())

        result = await self.conn.execute(stmt)

        return result.scalars().all()

    async def delete_chat(self, chat_id: int):
        stmt = select(Chat).where(Chat.id == chat_id)
        result = await self.conn.execute(stmt)
        chat = result.scalars().first()

        if chat:
            await self.conn.delete(chat)
            await self.conn.commit()
