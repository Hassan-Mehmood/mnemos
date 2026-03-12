from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from src.chats.chat_repository import ChatRepository
from src.chats.chat_schemas import AllChatsResponse, ChatInvoke, ChatMessagesResponse
from src.chats.chat_service import ChatService
from src.database.database import DBSession
from src.database.models import Chat
from src.logger import logger
from src.schemas.base_schema import SuccessResponse

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/invoke")
async def invoke_chat(
    chat_request: ChatInvoke, backgroundTasks: BackgroundTasks, conn: DBSession
):
    try:
        if chat_request.chat_id is None:
            try:
                chat_id = await ChatRepository.create_chat(
                    conn, chat_request.user_id, chat_request.message
                )
            except Exception as e:
                logger.error(f"Error creating chat: {str(e)} | {chat_request}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create chat",
                )

            chat_request.chat_id = chat_id

        else:
            chat_id = await ChatRepository.get_by_id(
                conn, chat_request.chat_id, columns=[Chat.id]
            )
            if not chat_id:
                logger.error(
                    f"Chat with ID {chat_request.chat_id} not found. | {chat_request}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
                )

        response = await ChatService.invoke(conn, chat_request, backgroundTasks)

        return {"response": response}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(f"An error occurred while processing the chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the chat",
        )


@router.get("/", response_model=SuccessResponse[List[AllChatsResponse]])
async def get_all_chats_for_user(conn: DBSession):
    try:
        chats = await ChatRepository.get_all(conn)

        return SuccessResponse[List[AllChatsResponse]](
            message="Success",
            data=[AllChatsResponse.model_validate(chat) for chat in chats],
            success=True,
        )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(f"An error occurred while processing the chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the chat",
        )


@router.get("/{chat_id}", response_model=SuccessResponse[List[ChatMessagesResponse]])
async def get_chat(chat_id: int, conn: DBSession):
    try:
        messages = await ChatRepository.get_chat_messages(conn=conn, id=chat_id)

        data = [ChatMessagesResponse.model_validate(message) for message in messages]

        return SuccessResponse[List[ChatMessagesResponse]](
            message="Success",
            data=data,
            success=True,
        )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(f"An error occurred while processing the chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the chat",
        )
