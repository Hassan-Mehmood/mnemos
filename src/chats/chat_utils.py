from collections.abc import Sequence

from src.chats.chat_enums import ChatMessageDict
from src.chats.chat_repository import ChatRepository
from src.chats.chat_service import ChatService
from src.core.database.database import DBSession
from src.core.database.models import ChatMessage
from src.memory.memory_log_repository import MemoryLogRepository
from src.users.user_repository import UserRepository


def format_chat_history(
    chat_history: Sequence[ChatMessage],
) -> list[ChatMessageDict]:
    return [{"role": entry.sender, "content": entry.content} for entry in chat_history]

    # formatted_history = []
    # for entry in chat_history:
    #     formatted_entry = {"role": entry.sender, "content": entry.content}
    #     formatted_history.append(formatted_entry)

    # return formatted_history


def get_chat_service(conn: DBSession):
    repo = ChatRepository(conn)
    user_repo = UserRepository(conn)
    memory_log_repo = MemoryLogRepository(conn)
    return ChatService(repo, user_repo, memory_log_repo)
