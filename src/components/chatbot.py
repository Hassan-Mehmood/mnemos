from openai import OpenAI

from src.chats.chat_enums import ChatMessageDict
from src.config import get_settings
from src.database.db_enums import MessageSender


class Chatbot:
    def __init__(self):
        self.client = OpenAI(api_key=get_settings().OPENAI_API_KEY)

    def invoke(self, input: str, history: list[ChatMessageDict]) -> str:

        history.append({"role": MessageSender.USER, "content": input})

        response = self.client.responses.create(
            model="gpt-4o-mini-2024-07-18",
            input=history,  # type: ignore
        )

        return response.output_text


chatbot = Chatbot()
