from typing import AsyncGenerator

from openai import OpenAI

from src.chats.chat_enums import ChatMessageDict
from src.config import get_settings


class Chatbot:
    def __init__(self):
        self.client = OpenAI(api_key=get_settings().OPENAI_API_KEY)

    def invoke(self, history: list[ChatMessageDict]) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=history,  # type: ignore
        )

        return response.choices[0].message.content or ""

    async def stream(self, history: list[ChatMessageDict]) -> AsyncGenerator[str, None]:
        stream = self.client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=history,  # type: ignore
            stream=True,
        )

        for event in stream:
            if event.choices[0].delta.content:
                yield event.choices[0].delta.content


chatbot = Chatbot()
