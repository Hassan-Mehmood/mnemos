from typing import List
from uuid import UUID

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.core.config import get_settings
from src.core.database.database import sessionmanager
from src.core.database.models import MemoryStructured
from src.core.logger import logger
from src.memory.long_term_memory import LongTermSemanticMemory
from src.memory.schemas.memory_extractor_schema import ExtractorOutput
from src.users.user_repository import UserRepository
from src.utils.system_prompts import EXTRACTION_PROMPT

settings = get_settings()


class MemoryExtractor:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

        self.memory_extractor_agent = Agent(
            model=OpenAIChatModel(
                settings.MEMORY_EXTRACTOR_MODEL,
                provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY),
            ),
            system_prompt=EXTRACTION_PROMPT,
            output_type=List[ExtractorOutput] | None,
        )

    async def extract(self, message: str, user_id: UUID) -> None:
        user_memories = await self.user_repository.get_user_memories(user_id)
        kv_pairs = await self.extract_kv_pairs(message, user_memories)

        await self.persist_memory(memories=kv_pairs, user_id=user_id)

    async def extract_kv_pairs(
        self, message: str, user_memories: List[MemoryStructured]
    ) -> List[ExtractorOutput] | None:
        user_memories_str = "\n".join(
            f'Key: {mem.key} | Value: "{mem.value}" (confidence: {mem.confidence})'
            for mem in user_memories
        )

        prompt = f"ALREADY EXISTING USER MEMORIES:\n\n{user_memories_str}\n\nCURRENT MESSAGE(the only extractable facts):\n{message}"

        print(f"Running MemoryExtractor with prompt:\n{prompt}\n---END OF PROMPT---")
        response = await self.memory_extractor_agent.run(prompt)
        logger.info(f"Extracted KV pairs: {response.output}")

        return response.output

    async def create_memory_embeddings(self, kv_pairs: List[ExtractorOutput]):
        pass

    async def persist_memory(
        self, memories: List[ExtractorOutput] | None, user_id: UUID
    ) -> None:

        logger.info(f"Memories to persist for user {user_id}: {memories}")

        if not memories:
            return

        # TODO: Comeback to this - we should ideally have a more robust way to handle DB sessions in background tasks
        async with sessionmanager.session() as session:
            repo = UserRepository(conn=session)

            long_term_memory = LongTermSemanticMemory()
            embeddings = long_term_memory.create_embeddings(
                [f"{mem.key}: {mem.value}" for mem in memories]
            )

            await repo.save_memories(
                kv_memories=memories,
                embeddings=embeddings,  # type: ignore
                user_id=user_id,
            )
