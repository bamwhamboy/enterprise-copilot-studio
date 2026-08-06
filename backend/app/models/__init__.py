"""SQLAlchemy ORM models.

All models inherit from ``app.database.base.Base``. They're imported
here so Alembic's autogenerate (and anything else that needs the full
metadata) discovers them via this single package.
"""

from app.models.copilot import Copilot, copilot_knowledge_sources
from app.models.conversation import ConversationMessage, ConversationSession
from app.models.document import Document
from app.models.knowledge_source import KnowledgeSource
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User

__all__ = [
    "Copilot",
    "KnowledgeSource",
    "Document",
    "copilot_knowledge_sources",
    "ConversationSession",
    "ConversationMessage",
    "Organization",
    "Role",
    "User",
    "RefreshToken",
]
