import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_utils import get_password_hash
from src.core.database.models import User
from src.users.user_schemas import UserCreate


class UserAuthRepository:
    def __init__(self, conn: AsyncSession):
        self.conn = conn

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.conn.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def create_user(self, user_create: UserCreate) -> User:
        hashed_password = get_password_hash(user_create.password)

        new_record = User(
            id=uuid.uuid4(),
            name=user_create.name,
            email=user_create.email,
            hashed_password=hashed_password,
        )

        self.conn.add(new_record)

        await self.conn.flush()
        return new_record
