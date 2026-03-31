from typing import List
from uuid import UUID

# from src.chats.chat_repository import ChatRepository
from src.memory.schemas.memory_extractor_schema import ExtractorOutput
from src.users.user_repository import UserRepository


class FactualMemory:
    def __init__(self, user_repository: UserRepository, max_length=10):
        self.max_length = max_length
        self.chat_repository = user_repository
        # self.memory: list[ChatMessageDict] = []

    async def retrieve(
        self, user_id: UUID, confidence_threshold: float = 7.0
    ) -> List[ExtractorOutput]:
        if confidence_threshold < 0 or confidence_threshold > 10:
            raise ValueError("Confidence threshold must be between 0 and 10.")

        user_memories = await self.chat_repository.get_user_memories(
            user_id=user_id, confidence_threshold=confidence_threshold
        )

        return [
            ExtractorOutput(
                key=mem.key,
                value=mem.value,
                confidence=mem.confidence,
            )
            for mem in user_memories
        ]
