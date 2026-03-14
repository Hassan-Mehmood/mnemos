from typing import AsyncGenerator, List

from openai import OpenAI

from src.chats.chat_enums import ChatMessageDict
from src.config import get_settings
from src.users.user_schemas import UserMemories
from src.utils.system_prompts import CHAT_PROMPT


class Chatbot:
    def __init__(self):
        self.client = OpenAI(api_key=get_settings().OPENAI_API_KEY)

    def invoke(self, message: str) -> str:
        # TODO: Consider a new approach for this.
        # Todo: There should an invoke method that can be called from anywhere with prompts included
        response = self.client.responses.create(
            model="gpt-4o-mini-2024-07-18", input=message
        )

        return response.output_text

    async def stream(
        self, history: list[ChatMessageDict], factual_memory: List[UserMemories]
    ) -> AsyncGenerator[str, None]:
        intructions = CHAT_PROMPT.format(
            factual_memory="\n".join(
                [
                    f'Key: {mem.key} | Value: "{mem.value}" (confidence: {mem.confidence}, superseded_by: {mem.superseded_by})'
                    for mem in factual_memory
                ]
            ),
        )

        stream = self.client.responses.create(
            model="gpt-4o-mini-2024-07-18",
            instructions=intructions,
            input=history,  # type: ignore
            stream=True,
        )

        for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta


chatbot = Chatbot()
