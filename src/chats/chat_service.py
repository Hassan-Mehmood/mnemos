from typing import List, Optional

from fastapi import BackgroundTasks

from src.chats.chat_repository import ChatRepository
from src.chats.chat_schemas import ChatInvoke
from src.components.chatbot import chatbot
from src.components.memory_extractor import memory_extractor
from src.components.memory_retriever import MemoryRetriever
from src.database.database import AsyncSession


class ChatService:
    def __init__(self, chat_repository: ChatRepository):
        self.chat_repository = chat_repository

    async def invoke(
        self, payload: ChatInvoke, backgroundTasks: BackgroundTasks
    ) -> str:
        if payload.chat_id is None:
            raise ValueError("Chat ID must be provided for invoking chat.")

        memory_retriever = MemoryRetriever(chat_repository=self.chat_repository)

        memory = await memory_retriever.retrieve(
            chat_id=payload.chat_id,
            query=payload.message,
        )

        response = chatbot.invoke(memory)

        backgroundTasks.add_task(memory_extractor.run, payload.message, payload.user_id)
        backgroundTasks.add_task(
            self.chat_repository.save_user_bot_exchange,
            payload.chat_id,
            payload.message,
            response,
        )

        return response

    async def create(self, user_id: int, name: str) -> int:
        return await self.chat_repository.create_chat(user_id, name)

    async def get_all(self):
        return await self.chat_repository.get_all()

    async def get_by_id(
        self,
        chat_id: int,
        columns: Optional[List] = None,
        load: Optional[List] = None,
    ):
        return await self.chat_repository.get_by_id(chat_id, columns=columns, load=load)

    async def get_chat_messages(self, id: int):
        return await self.chat_repository.get_chat_messages(id)
