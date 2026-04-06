from typing import TypedDict

from src.core.database.db_enums import MessageSender


class ChatMessageDict(TypedDict):
    role: MessageSender
    content: str
