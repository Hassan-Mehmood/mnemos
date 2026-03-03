from fastapi import APIRouter

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/")
def get_chats():
    return {"message": "List of chats"}
