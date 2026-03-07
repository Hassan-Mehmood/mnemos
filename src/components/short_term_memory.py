from src.chats.chat_enums import ChatMessageDict
from src.chats.chat_repository import ChatRepository
from src.chats.chat_schemas import ChatInvoke

# from src.chats.chat_utils import format_chat_history
from src.database.database import AsyncSession
from src.database.db_enums import MessageSender


class ShortTermMemory:
    def __init__(self, max_length=10):
        self.max_length = max_length
        self.memory: list[ChatMessageDict] = []

    async def add(self, payload: ChatInvoke, conn: AsyncSession):
        if payload.chat_id is None:
            raise ValueError("Chat ID must be provided for invoking chat.")

        chat_history = await ChatRepository.get_history_by_id(conn, payload.chat_id)
        for entry in chat_history:
            self.memory.append({"role": entry.sender, "content": entry.content})

            # Check if adding the new message would exceed the max length
            # +1 for the new message being added
            if len(self.memory) + 1 > self.max_length:
                print(
                    f"Memory limit exceeded. Current memory length: {len(self.memory)}, Max length: {self.max_length}"
                )
                self.memory.pop(0)

        self.memory.append({"role": MessageSender.USER, "content": payload.message})

    def get_memory(self):
        return self.memory
