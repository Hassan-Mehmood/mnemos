from fastapi import BackgroundTasks

from src.chats.chat_repository import ChatRepository
from src.chats.chat_schemas import ChatInvoke
from src.components.chatbot import chatbot
from src.components.memory_extractor import memory_extractor
from src.components.memory_retriever import MemoryRetriever
from src.database.database import AsyncSession


class ChatService:
    @staticmethod
    async def invoke(
        conn: AsyncSession, payload: ChatInvoke, backgroundTasks: BackgroundTasks
    ) -> str:
        if payload.chat_id is None:
            raise ValueError("Chat ID must be provided for invoking chat.")

        memory_retriever = MemoryRetriever(conn=conn)

        memory = await memory_retriever.retrieve(
            chat_id=payload.chat_id,
            query=payload.message,
        )

        response = chatbot.invoke(memory)

        backgroundTasks.add_task(memory_extractor.run, payload.message, payload.user_id)
        backgroundTasks.add_task(
            ChatRepository.save_user_bot_exchange,
            payload.chat_id,
            payload.message,
            response,
        )

        return response
