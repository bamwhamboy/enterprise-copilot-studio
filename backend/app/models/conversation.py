"""Conversation memory ORM models.

A ConversationSession is the unit of isolation: one per (user, copilot)
conversation thread. ConversationMessage rows are the short-term/session
memory itself -- the ordered history the chat orchestrator loads back
in on each turn.

Kept in app/models/ (not app/memory/) for the same reason every other
entity lives here: a single, Alembic-discoverable source of persistence
schema. app/memory/ holds the *service* logic that operates on these
models, mirroring how knowledge_engine/ holds service logic over
app/models/document.py.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ConversationSession(Base):
    """A single conversation thread, isolated by user_id + copilot_id.

    No FK to Copilot: user_id/copilot_id are plain identifiers so a
    session can exist even for ad-hoc/anonymous testing without
    requiring a real Copilot row -- matches this sprint's scope (chat
    runtime, not full account/auth modeling).
    """

    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    copilot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )


class ConversationMessage(Base):
    """A single turn (user or assistant) within a conversation session."""

    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    # "user" | "assistant" | "system"
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Citations / tool calls attached to an assistant message, as JSON text
    # (kept simple -- a JSONB column is a reasonable future upgrade, not
    # required for this sprint's scope).
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    session: Mapped["ConversationSession"] = relationship(
        "ConversationSession", back_populates="messages"
    )
