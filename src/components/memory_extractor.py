from typing import List

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

from src.config import get_settings
from src.database.database import sessionmanager
from src.database.models import MemoryStructured
from src.logger import logger
from src.utils.system_prompts import EXTRACTION_PROMPT

settings = get_settings()


class ExtractorOutput(BaseModel):
    key: str = Field(..., description="The key of the memory")
    value: str = Field(..., description="The value of the memory")
    confidence: float = Field(
        le=10, ge=0, description="The confidence score of the key and value"
    )


class MemoryExtractor:
    def __init__(self) -> None:
        self.memory_extractor = Agent(
            model=GroqModel(
                "openai/gpt-oss-20b",
                provider=GroqProvider(api_key=settings.GROQ_API_KEY),
            ),
            system_prompt=EXTRACTION_PROMPT,
            output_type=List[ExtractorOutput],
        )

    async def run(self, message: str, user_id: int) -> List[ExtractorOutput]:
        response = await self.memory_extractor.run(message)
        logger.info(f"{response.output}")

        await self.persist_memory(response.output, user_id)

        return response.output

    async def persist_memory(self, memories: List[ExtractorOutput], user_id: int):
        async with sessionmanager.session() as session:
            for memory in memories:
                record = MemoryStructured(
                    user_id=user_id,
                    key=memory.key,
                    value=memory.value,
                    confidence=memory.confidence,
                )

                session.add(record)

            await session.commit()


memory_extractor = MemoryExtractor()
