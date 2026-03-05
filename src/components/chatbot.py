from openai import OpenAI

from src.config import get_settings


class Chatbot:
    def __init__(self):
        self.client = OpenAI(api_key=get_settings().OPENAI_API_KEY)

    def invoke(self, input: str):
        response = self.client.responses.create(
            model="gpt-4o-mini-2024-07-18",
            input=input,
        )

        return response.output_text


chatbot = Chatbot()
