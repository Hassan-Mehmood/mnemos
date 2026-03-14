import uuid
from typing import List

from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

from src.config import get_settings
from src.database.database import sessionmanager
from src.logger import logger
from src.schemas.memory_extractor_schema import ExtractorOutput
from src.users.user_repository import UserRepository
from src.utils.system_prompts import EXTRACTION_PROMPT

settings = get_settings()


class MemoryExtractor:
    def __init__(self) -> None:
        self.memory_extractor_agent = Agent(
            model=GroqModel(
                "openai/gpt-oss-20b",
                provider=GroqProvider(api_key=settings.GROQ_API_KEY),
            ),
            system_prompt=EXTRACTION_PROMPT,
            output_type=List[ExtractorOutput],
        )

    async def run(self, message: str, user_id: uuid.UUID) -> List[ExtractorOutput]:
        response = await self.memory_extractor_agent.run(message)
        logger.info(f"{response.output}")

        await self.persist_memory(response.output, user_id)

        return response.output

    async def persist_memory(self, memories: List[ExtractorOutput], user_id: uuid.UUID):
        async with sessionmanager.session() as session:
            repo = UserRepository(conn=session)
            await repo.save_memories(memories, user_id)


memory_extractor = MemoryExtractor()
