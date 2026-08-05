"""Schemas for the chat API."""

import uuid

from pydantic import BaseModel, Field

from app.knowledge_engine.models import Citation


class ChatRequest(BaseModel):
    copilot_id: uuid.UUID
    user_id: str = Field(min_length=1, max_length=255)
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
