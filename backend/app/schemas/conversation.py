"""Schemas for conversation memory."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel

MessageRole = Literal["user", "assistant", "system"]


class ConversationMessageRead(ORMBaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class ConversationSessionRead(ORMBaseModel):
    id: uuid.UUID
    user_id: str
    copilot_id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageRead] = Field(default_factory=list)
