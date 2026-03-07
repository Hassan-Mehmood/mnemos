from openai import OpenAI

from src.chats.chat_enums import ChatMessageDict
from src.config import get_settings


class Chatbot:
    def __init__(self):
        self.client = OpenAI(api_key=get_settings().OPENAI_API_KEY)

    def invoke(self, history: list[ChatMessageDict]) -> str:

        response = self.client.responses.create(
            model="gpt-4o-mini-2024-07-18",
            input=history,  # type: ignore
        )

        return response.output_text


chatbot = Chatbot()
