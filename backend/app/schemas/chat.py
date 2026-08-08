"""Schemas for the chat API."""

import uuid

from pydantic import BaseModel, Field

from app.knowledge_engine.models import Citation


class ChatRequest(BaseModel):
    copilot_id: uuid.UUID
    # Sprint 6: no longer required from the client -- the authenticated
    # user's id always overrides this field in app/api/v1/chat.py,
    # regardless of what's sent here. Kept (rather than removed) only
    # so any old client payload still validates instead of erroring.
    user_id: str | None = Field(default=None, max_length=255)
    # Tenant isolation follow-up: same pattern as user_id above -- always
    # overridden at the API boundary (app/api/v1/chat.py) from the
    # authenticated user's own organization, never trusted from the
    # client. None means "unscoped" (super_admin) rather than "no
    # organization" -- see security/dependencies.py's
    # scoped_organization_id().
    organization_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=8000)
    knowledge_source_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    message: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float


class ChatStreamEvent(BaseModel):
    """One SSE event. ``event`` distinguishes chunk/citations/done/error frames."""

    event: str
    data: dict
