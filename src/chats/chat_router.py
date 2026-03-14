import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.chats.chat_schemas import AllChatsResponse, ChatInvoke, ChatMessagesResponse
from src.chats.chat_service import ChatService
from src.chats.chat_utils import get_chat_service
from src.database.models import Chat
from src.logger import logger
from src.schemas.base_schema import SuccessResponse

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/invoke", response_class=StreamingResponse)
async def invoke_chat(
    chat_request: ChatInvoke,
    backgroundTasks: BackgroundTasks,
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        if chat_request.chat_id is None:
            try:
                chat_id = await chat_service.create(
                    chat_request.user_id, chat_request.message
                )

                backgroundTasks.add_task(
                    chat_service.name_chat, chat_id, chat_request.message
                )
            except Exception as e:
                logger.error(f"Error creating chat: {str(e)} | {chat_request}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create chat",
                )

            chat_request.chat_id = chat_id

        else:
            chat_id = await chat_service.get_by_id(
                chat_request.chat_id, columns=[Chat.id]
            )
            if not chat_id:
                logger.error(
                    f"Chat with ID {chat_request.chat_id} not found. | {chat_request}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
                )

        stream = await chat_service.invoke(chat_request, backgroundTasks)

        return StreamingResponse(
            stream,
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(f"An error occurred while processing the chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the chat",
        )


@router.get("", response_model=SuccessResponse[List[AllChatsResponse]])
async def get_all_chats_for_user(chat_service: ChatService = Depends(get_chat_service)):
    try:
        chats = await chat_service.get_all()

        return SuccessResponse[List[AllChatsResponse]](
            success=True,
            message="Success",
            data=[AllChatsResponse.model_validate(chat) for chat in chats],
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
async def get_chat(
    chat_id: uuid.UUID, chat_service: ChatService = Depends(get_chat_service)
):
    try:
        messages = await chat_service.get_chat_messages(id=chat_id)

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


@router.delete("/{chat_id}", response_model=SuccessResponse[None])
async def delete_chat(
    chat_id: uuid.UUID, chat_service: ChatService = Depends(get_chat_service)
):
    try:
        await chat_service.delete_chat(chat_id)

        return SuccessResponse[None](
            success=True,
            message="Chat deleted successfully",
            data=None,
        )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        logger.error(f"An error occurred while deleting the chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the chat",
        )
