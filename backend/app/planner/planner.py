"""Planner interface.

Defines the contract a future multi-agent orchestrator (LangGraph-based
or otherwise) will implement to decide and carry out a copilot's
workflow. This sprint defines the interface only — no concrete planner,
no LangGraph, no execution engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field

from app.planner.task import Task


class PlanStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanResult(BaseModel):
    """The outcome of executing a plan's tasks."""

    tasks: list[Task] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.PLANNED
    summary: str | None = None


class Planner(ABC):
    """Interface for deciding and carrying out a copilot's workflow.

    Concrete implementations (e.g. a LangGraph-based planner) arrive in
    a later sprint. Nothing in this codebase instantiates this class
    yet — it exists purely to fix the contract other modules (the LLM
    Gateway, Guardrails, Prompt Engine) will be composed behind once a
    real planner exists.
    """

    @abstractmethod
    async def plan(self, goal: str, context: dict[str, str] | None = None) -> list[Task]:
        """Decompose a goal into an ordered (or dependency-linked) list of tasks."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, tasks: list[Task]) -> PlanResult:
        """Carry out a previously-produced list of tasks."""
        raise NotImplementedError
