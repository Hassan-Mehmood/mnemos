from typing import TypedDict

from src.database.db_enums import MessageSender


class ChatMessageDict(TypedDict):
    role: MessageSender
    content: str
