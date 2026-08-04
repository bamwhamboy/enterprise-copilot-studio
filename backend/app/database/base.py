"""Declarative base for all future SQLAlchemy ORM models.

Every model added under ``app/models/`` should inherit from ``Base`` so
Alembic's autogenerate can discover it via this shared metadata.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base class for all ORM models."""
