from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base_schema import SuccessResponse
from src.core.auth_utils import create_access_token, verify_password
from src.core.database.database import get_db
from src.users.user_auth_repository import UserAuthRepository
from src.users.user_schemas import Token, UserCreate, UserLogin, UserResponse

DBSession = Annotated[AsyncSession, Depends(get_db)]

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=SuccessResponse[UserResponse])
async def register(user: UserCreate, conn: DBSession):
    repo = UserAuthRepository(conn)

    existing_user = await repo.get_user_by_email(user.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    new_user = await repo.create_user(user)
    await conn.commit()

    return SuccessResponse(
        message="User registered successfully",
        data=UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=SuccessResponse[Token])
async def login(user_credentials: UserLogin, conn: DBSession):
    repo = UserAuthRepository(conn)
    user = await repo.get_user_by_email(user_credentials.email)

    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    return SuccessResponse(
        message="Login successful",
        data=Token(access_token=access_token, token_type="bearer"),
    )
