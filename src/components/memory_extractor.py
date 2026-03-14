import uuid
from typing import List

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.config import get_settings
from src.database.database import sessionmanager
from src.logger import logger
from src.schemas.memory_extractor_schema import ExtractorOutput
from src.users.user_repository import UserRepository
from src.utils.system_prompts import EXTRACTION_PROMPT

settings = get_settings()


class MemoryExtractor:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

        self.memory_extractor_agent = Agent(
            model=OpenAIChatModel(
                "gpt-4o-mini-2024-07-18",
                provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY),
            ),
            system_prompt=EXTRACTION_PROMPT,
            output_type=List[ExtractorOutput],
        )

    async def run(self, message: str, user_id: uuid.UUID) -> List[ExtractorOutput]:
        user_memories = await self.user_repository.get_user_memories(user_id)

        user_memories_str = "\n".join(
            [
                f'Key: {mem.key} | Value: "{mem.value}" (confidence: {mem.confidence}, superseded_by: {mem.superseded_by})'
                for mem in user_memories
            ]
        )

        new_prompt = f"""
USER MEMORIES:
{user_memories_str}

CURRENT MESSAGE:
{message}
"""

        logger.info(f"Running memory extractor with prompt: {new_prompt}")
        response = await self.memory_extractor_agent.run(new_prompt)
        logger.info(f"{response.output}")

        await self.persist_memory(response.output, user_id)

        return response.output

    async def persist_memory(self, memories: List[ExtractorOutput], user_id: uuid.UUID):
        async with sessionmanager.session() as session:
            repo = UserRepository(conn=session)
            await repo.save_memories(memories, user_id)
