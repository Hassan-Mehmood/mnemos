from uuid import UUID

from pydantic import EmailStr

from src.base_schema import BaseSchema


class UserCreate(BaseSchema):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseSchema):
    email: EmailStr
    password: str


class UserResponse(BaseSchema):
    id: UUID
    name: str
    email: EmailStr


class Token(BaseSchema):
    access_token: str
    token_type: str
    email: EmailStr
    name: str
