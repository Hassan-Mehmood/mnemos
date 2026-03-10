from fastapi import BackgroundTasks

from src.chats.chat_repository import ChatRepository
from src.chats.chat_schemas import ChatInvoke

# from src.chats.chat_utils import format_chat_history
from src.components.chatbot import chatbot
from src.components.memory_retriever import MemoryRetriever
from src.database.database import AsyncSession
from src.database.db_enums import MessageSender


class ChatService:
    @staticmethod
    async def invoke(
        conn: AsyncSession, payload: ChatInvoke, backgroundTasks: BackgroundTasks
    ) -> str:
        if payload.chat_id is None:
            raise ValueError("Chat ID must be provided for invoking chat.")

        memory_retriever = MemoryRetriever(conn=conn)

        memory = await memory_retriever.retrieve(
            chat_id=payload.chat_id, query=payload.message
        )

        response = chatbot.invoke(memory)

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
