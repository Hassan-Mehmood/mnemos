from src.components.chatbot import chatbot


class ChatService:
    @staticmethod
    def invoke(message: str) -> str:
        response = chatbot.invoke(message)
        return response
