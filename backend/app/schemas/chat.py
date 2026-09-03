"""Schemas for the chat API."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.knowledge_engine.models import Citation


class ChatRequest(BaseModel):
    copilot_id: uuid.UUID
    user_id: str | None = Field(default=None, max_length=255)
    organization_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=8000)
    knowledge_source_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    message: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float
    evaluation_status: Literal["passed", "corrected", "disabled", "human_review_required"] = "passed"
    evaluation_attempts: int = 0
    human_review_required: bool = False


class ChatStreamEvent(BaseModel):
    """One SSE event. ``event`` distinguishes chunk/done/error frames."""

    event: str
    data: dict
