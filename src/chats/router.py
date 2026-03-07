from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from src.chats.chat_repository import ChatRepository
from src.chats.chat_schemas import ChatInvoke
from src.chats.chat_service import ChatService
from src.database.database import DBSession

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/invoke")
async def invoke_chat(
    chat_request: ChatInvoke, backgroundTasks: BackgroundTasks, conn: DBSession
):
    try:
        if chat_request.chat_id is None:
            try:
                chat_id = await ChatRepository.create_chat(conn, chat_request.user_id)
            except Exception as e:
                print(f"Error creating chat: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create chat",
                )

            chat_request.chat_id = chat_id

        else:
            chat_id = await ChatRepository.get_chat_by_id(conn, chat_request.chat_id)
            if not chat_id:
                print(f"Chat with ID {chat_request.chat_id} not found.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
                )

        response = await ChatService.invoke(conn, chat_request, backgroundTasks)

        return {"response": response}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the chat: {str(e)}",
        )
