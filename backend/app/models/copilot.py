"""Copilot ORM model.

A Copilot is composed from zero or more KnowledgeSources (many-to-many —
a single knowledge source, e.g. a shared SharePoint site, can back more
than one copilot).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Table, Column, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

# Sprint 1 HITL foundation: the safe, backward-compatible starting
# capability set. Existing copilots (pre-migration) get exactly this
# via the migration's server_default; new copilots get it via this
# same dict, so both paths agree. Adding a future capability (e.g.
# retrieval/graph/agentic toggles) means adding a key here -- no
# schema/column change, since the column is JSONB.
DEFAULT_CAPABILITIES: dict[str, object] = {"human_in_the_loop": False}

# Association table for the Copilot <-> KnowledgeSource many-to-many relationship.
copilot_knowledge_sources = Table(
    "copilot_knowledge_sources",
    Base.metadata,
    Column(
        "copilot_id",
        UUID(as_uuid=True),
        ForeignKey("copilots.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "knowledge_source_id",
        UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Copilot(Base):
    """An enterprise AI copilot (e.g. "HR Copilot")."""

    __tablename__ = "copilots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Sprint 6 multi-tenancy: nullable for backward compatibility with rows
    # created before Sprint 6 (and the still-open, unauthenticated-in-tests
    # JSON creation path). NULL means "unscoped" -- invisible to normal
    # tenant-scoped queries, visible only to super_admin. See
    # app/services/copilot_service.py for the scoping logic.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, default="hr")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    # Kept in sync with Settings.DEFAULT_LLM_MODEL (app/core/config.py) so a
    # newly-created copilot's own default doesn't drift from the platform
    # default -- both should point at the same current, real model id.
    model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="openai/gpt-oss-120b"
    )
    # Sprint 1 HITL foundation: JSONB so future capability keys
    # (retrieval/graph/agentic toggles, etc.) never need another
    # migration -- just a new key in DEFAULT_CAPABILITIES and the
    # corresponding Pydantic field in app/schemas/copilot.py.
    # NOT NULL with both a Python-side default (new ORM instances
    # built in Python before insert) and a matching server_default
    # (existing rows backfilled by the migration, and any insert that
    # bypasses the ORM). Deliberately does not implement any HITL
    # workflow/review-queue logic -- this is configuration only.
    capabilities: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: dict(DEFAULT_CAPABILITIES),
        server_default=text("'{\"human_in_the_loop\": false}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    knowledge_sources: Mapped[list["KnowledgeSource"]] = relationship(
        "KnowledgeSource",
        secondary=copilot_knowledge_sources,
        back_populates="copilots",
    )
