from pydantic import BaseModel


class ChatInvoke(BaseModel):
    chat_id: int | None = None
    user_id: int
    message: str
