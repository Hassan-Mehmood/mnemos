from fastapi import BackgroundTasks

from src.chats.chat_repository import ChatRepository
from src.chats.chat_schemas import ChatInvoke
from src.chats.chat_utils import format_chat_history
from src.components.chatbot import chatbot
from src.database.database import AsyncSession
from src.database.db_enums import MessageSender


class ChatService:
    @staticmethod
    async def invoke(
        conn: AsyncSession, payload: ChatInvoke, backgroundTasks: BackgroundTasks
    ) -> str:
        if payload.chat_id is None:
            raise ValueError("Chat ID must be provided for invoking chat.")

        chat_history = await ChatRepository.get_history_by_id(conn, payload.chat_id)

        chat_history = format_chat_history(chat_history)
        response = chatbot.invoke(payload.message, chat_history)

        backgroundTasks.add_task(
            ChatRepository.save_message,
            conn,
            payload.chat_id,
            payload.message,
            MessageSender.USER,
        )
        backgroundTasks.add_task(
            ChatRepository.save_message,
            conn,
            payload.chat_id,
            response,
            MessageSender.BOT,
        )

        return response
