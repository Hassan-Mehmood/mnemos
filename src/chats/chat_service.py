from typing import List, Optional
from uuid import UUID

from fastapi import BackgroundTasks

from src.chats.chat_repository import ChatRepository
from src.chats.chat_schemas import ChatInvoke
from src.components.chatbot import chatbot
from src.memory.memory_extractor import MemoryExtractor
from src.memory.memory_log_repository import MemoryLogRepository
from src.memory.memory_retriever import MemoryRetriever
from src.users.user_repository import UserRepository


class ChatService:
    def __init__(
        self,
        chat_repository: ChatRepository,
        user_repository: UserRepository,
        memory_log_repository: MemoryLogRepository,
    ) -> None:
        self.chat_repository = chat_repository
        self.user_repository = user_repository

        self.memory_extractor = MemoryExtractor(user_repository=self.user_repository)
        self.memory_retriever = MemoryRetriever(
            chat_repository=self.chat_repository,
            user_repository=self.user_repository,
            memory_log_repository=memory_log_repository,
        )

    async def invoke(self, payload: ChatInvoke, backgroundTasks: BackgroundTasks):
        message_id = await self.chat_repository.save_user_message(
            chat_id=payload.chat_id,
            content=payload.message,
        )

        memory = await self.memory_retriever.retrieve(
            chat_id=payload.chat_id,
            user_id=payload.user_id,
            message_id=message_id,
            query=payload.message,
        )

        await self.memory_retriever.memory_log_repository.update_token_count(
            message_id=message_id,
            token_count=memory.tokens_used,
        )

        async def generator():
            full_response = ""
            async for chunk in chatbot.stream(
                history=memory.short_term,
                factual_memory=memory.factual,
                semantic_memory=memory.semantic,
            ):
                full_response += chunk
                yield chunk.encode("utf-8")

            backgroundTasks.add_task(
                self.memory_extractor.extract,
                payload.message,
                payload.user_id,
            )

            backgroundTasks.add_task(
                self.chat_repository.save_bot_message,
                payload.chat_id,  # type: ignore
                full_response,
            )

        return generator()

    async def create(self, user_id: UUID, name: str) -> UUID:
        return await self.chat_repository.create_chat(user_id, name)

    async def create_with_id(self, id: UUID, user_id: UUID, name: str) -> UUID:
        return await self.chat_repository.create_chat_with_id(id, user_id, name)

    async def get_all(self):
        return await self.chat_repository.get_all()

    async def get_by_id(
        self,
        chat_id: UUID,
        columns: Optional[List] = None,
        load: Optional[List] = None,
    ):
        return await self.chat_repository.get_by_id(chat_id, columns=columns, load=load)

    async def get_chat_messages(self, id: UUID):
        return await self.chat_repository.get_chat_messages(id)

    async def delete_chat(self, chat_id: UUID):
        await self.chat_repository.delete_chat(chat_id)

    async def name_chat(self, chat_id: UUID, message: str):
        """Generate a name for the chat based on its first message."""
        # TODO: Consider a new approach for this.
        prompt = f'Generate a concise and descriptive name for a chat based on the following message: "{message}"'
        response = chatbot.invoke(prompt)

        await self.chat_repository.update_chat_name(chat_id, response.strip())
