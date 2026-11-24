from datetime import datetime, timezone
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ChatSession(Base):
    __tablename__ = "sessions"
    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String, default=now_iso)
    messages: Mapped[list["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=now_iso, nullable=False)
    session: Mapped[ChatSession] = relationship(back_populates="messages")

Index("ix_messages_session_created", Message.session_id, Message.created_at, Message.id)
