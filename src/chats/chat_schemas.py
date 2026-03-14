import uuid

from src.schemas.base_schema import BaseSchema


class ChatInvoke(BaseSchema):
    chat_id: uuid.UUID | None = None
    user_id: uuid.UUID
    message: str


class AllChatsResponse(BaseSchema):
    id: uuid.UUID
    name: str
    # last_message_at: Datetime


class ChatMessagesResponse(BaseSchema):
    id: uuid.UUID
    content: str
    sender: str
