"""Role ORM model.

A small reference table (seeded via Alembic migration with the five
enterprise roles) rather than a hardcoded enum, so new roles can be
added operationally without a code change.
"""

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

# Canonical role names, seeded by the Sprint 6 migration. Referenced by
# name (not id) throughout the app so authorization checks stay readable.
SUPER_ADMIN = "super_admin"
ORGANIZATION_ADMIN = "organization_admin"
COPILOT_CREATOR = "copilot_creator"
KNOWLEDGE_MANAGER = "knowledge_manager"
END_USER = "end_user"

ALL_ROLES = [SUPER_ADMIN, ORGANIZATION_ADMIN, COPILOT_CREATOR, KNOWLEDGE_MANAGER, END_USER]


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship("User", back_populates="role")
