from typing import List, Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.config import get_settings
from src.core.database import Base
from src.core.database.db_enums import MessageSender

settings = get_settings()


class User(Base):
    __tablename__ = "user"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
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
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))

    name: Mapped[str] = mapped_column(String(), nullable=False)
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="chat", cascade="all, delete-orphan"
    )

    user: Mapped["User"] = relationship(back_populates="chats")

    last_message_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    chat_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat.id"),
    )

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


class MemoryEmbedding(Base):
    __tablename__ = "memory_embedding"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    memory_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("memory_structured.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[List[float]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSIONS)
    )

    user: Mapped["User"] = relationship("User")
    memory: Mapped[Optional["MemoryStructured"]] = relationship("MemoryStructured")

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    __table_args__ = (
        Index(
            "idx_memory_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self):
        return f"MemoryEmbedding(id={self.id!r}, user_id={self.user_id!r}, content={self.content!r})"


class MemoryStructured(Base):
    __tablename__ = "memory_structured"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    superseded_by: Mapped[Optional[UUID]] = mapped_column(
        Uuid,
        nullable=True,
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

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_message.id", ondelete="CASCADE")
    )

    gate_decision: Mapped[str] = mapped_column(String(30))

    gate_reason: Mapped[Optional[str]] = mapped_column(String(), nullable=True)

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
