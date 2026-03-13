from src.chats.chat_enums import ChatMessageDict
from src.chats.chat_repository import ChatRepository
from src.database.db_enums import MessageSender
from src.logger import logger


class ShortTermMemory:
    def __init__(self, chat_repository: ChatRepository, max_length=10):
        self.max_length = max_length
        self.chat_repository = chat_repository
        self.memory: list[ChatMessageDict] = []

    async def prepare(self, chat_id: int, query: str):
        chat_history = await self.chat_repository.get_history_by_id(chat_id)

        logger.info(f"Total messages in chat history: {len(chat_history)}")

        for entry in chat_history:
            self.memory.append({"role": entry.sender, "content": entry.content})

            # Check if adding the new message would exceed the max length
            # +1 for the new message being added
            if len(self.memory) + 1 > self.max_length:
                self.memory.pop(0)

        self.memory.append({"role": MessageSender.USER, "content": query})

        return self.memory

    def get_memory(self):
        return self.memory

    def append_message(self, role: str, content: str):
        message = ChatMessageDict(
            role=MessageSender.USER if role == "user" else MessageSender.BOT,
            content=content,
        )
        self.memory.append(message)
