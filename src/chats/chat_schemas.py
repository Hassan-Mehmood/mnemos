from src.schemas.base_schema import BaseSchema


class ChatInvoke(BaseSchema):
    chat_id: int | None = None
    user_id: int
    message: str


class AllChatsResponse(BaseSchema):
    id: int
    name: str
    # last_message_at: Datetime


class ChatMessagesResponse(BaseSchema):
    id: int
    content: str
    sender: str
