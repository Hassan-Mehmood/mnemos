from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
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

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
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

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __repr__(self):
        return f"Chat(id={self.id!r}, user_id={self.user_id!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r}), messages={len(self.messages)}"


class ChatMessage(Base):
    __tablename__ = "chat_message"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id"))

    content: Mapped[str] = mapped_column(String())
    sender: Mapped[MessageSender] = mapped_column(String(20))

    chat: Mapped[Chat] = relationship(back_populates="messages")

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __repr__(self):
        return f"ChatMessage(id={self.id!r}, chat_id={self.chat_id!r}, sender={self.sender!r}, created_at={self.created_at!r}, updated_at={self.updated_at!r}), content={self.content}"


class MemoryStructured(Base):
    __tablename__ = "memory_structured"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Self-referential — points to the newer memory that replaced this one
    superseded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("memory_structured.id"), nullable=True
    )
    superseded_by_memory: Mapped[Optional["MemoryStructured"]] = relationship(
        "MemoryStructured", remote_side="MemoryStructured.id"
    )

    user: Mapped["User"] = relationship("User")

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    __table_args__ = (
        Index(
            "idx_active_memory_unique",
            "user_id",
            "key",
            unique=True,
            postgresql_where=(superseded_by == None),  # noqa: E711
        ),
    )

    def __repr__(self):
        return f"MemoryStructured(id={self.id!r}, user_id={self.user_id!r}, key={self.key!r}, value={self.value!r}, confidence={self.confidence!r})"


class MemoryLog(Base):
    __tablename__ = "memory_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_message.id"))

    # Gate decision: "SKIP" | "RETRIEVE" | "RETRIEVE_AND_STORE"
    gate_decision: Mapped[str] = mapped_column(String(30))

    # Which rule/signal triggered — e.g. "personal_signal: my"
    gate_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Memory IDs fetched vs actually used by LLM — gap between these is your training signal
    retrieved_ids: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    used_memory_ids: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship("User")
    message: Mapped["ChatMessage"] = relationship("ChatMessage")

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __repr__(self):
        return f"MemoryLog(id={self.id!r}, user_id={self.user_id!r}, gate_decision={self.gate_decision!r}, token_count={self.token_count!r}, latency_ms={self.latency_ms!r})"
