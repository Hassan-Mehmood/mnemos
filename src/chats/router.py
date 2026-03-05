from fastapi import APIRouter
from pydantic import BaseModel

from src.chats.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


class ChatRequest(BaseModel):
    message: str


@router.post("/invoke")
def invoke_chat(chat_request: ChatRequest):

    response = ChatService.invoke(chat_request.message)

    return {"response": response}
