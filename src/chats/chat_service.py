from src.chats.chat_repository import ChatRepository
from src.chats.chat_schemas import ChatRequest
from src.components.chatbot import chatbot
from src.database.database import AsyncSession


class ChatService:
    @staticmethod
    async def invoke(conn: AsyncSession, payload: ChatRequest) -> str:

        chat_history = await ChatRepository.get_history_by_id(conn, payload.chat_id)

        response = chatbot.invoke(payload.message, chat_history)
        return response
