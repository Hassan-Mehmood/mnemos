from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.db_enums import MessageSender


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[Optional[str]]

    chats: Mapped[List["Chat"]] = relationship(
        "Chat", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"


class Chat(Base):
    __tablename__ = "chat"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="chat", cascade="all, delete-orphan"
    )

    user: Mapped["User"] = relationship(back_populates="chats")

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))

    def __repr__(self):
        return f"Chat(id={self.id!r}, user_id={self.user_id!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r}), messages={len(self.messages)}"


class ChatMessage(Base):
    __tablename__ = "chat_message"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id"))

    content: Mapped[str] = mapped_column(String())
    sender: Mapped[MessageSender] = mapped_column(String(20))

    chat: Mapped[Chat] = relationship(back_populates="messages")

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))

    def __repr__(self):
        return f"ChatMessage(id={self.id!r}, chat_id={self.chat_id!r}, sender={self.sender!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r}), content={self.content}"
