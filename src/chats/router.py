from fastapi import APIRouter

from src.chats.chat_schemas import ChatRequest
from src.chats.chat_service import ChatService
from src.database.database import DBSession

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/invoke")
async def invoke_chat(chat_request: ChatRequest, conn: DBSession):

    response = await ChatService.invoke(conn, chat_request)

    return {"response": response}
