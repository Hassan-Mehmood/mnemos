import uuid

# from src.chats.chat_repository import ChatRepository
from src.users.user_repository import UserRepository


class FactualMemory:
    def __init__(self, user_repository: UserRepository, max_length=10):
        self.max_length = max_length
        self.chat_repository = user_repository
        # self.memory: list[ChatMessageDict] = []

    async def prepare(self, user_id: uuid.UUID, query: str):
        user_memories = await self.chat_repository.get_user_memories(user_id=user_id)
        return user_memories
