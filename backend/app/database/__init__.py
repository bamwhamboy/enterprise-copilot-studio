"""Database engine, session, and declarative base.

This package wires up SQLAlchemy against PostgreSQL. No ORM models are
defined yet — ``app/models/`` is a placeholder package reserved for the
next phase — but the engine/session machinery is fully functional so
future models and Alembic migrations can build on it immediately.
"""
