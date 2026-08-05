"""Task model used by the Planner interface.

A ``Task`` is a unit of future work a planner would produce and an
executor would carry out. This sprint defines the shape only — no
scheduler, no LangGraph, no execution logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """A single unit of work within a plan.

    ``depends_on`` lists other task ids that must complete first —
    enough structure to express a DAG without committing to any
    particular execution engine.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    status: TaskStatus = TaskStatus.PENDING
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    result: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
