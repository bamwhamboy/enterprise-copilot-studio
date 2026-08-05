"""Tests for app.planner — the Planner interface is abstract by design."""

import pytest

from app.planner.planner import PlanResult, PlanStatus, Planner
from app.planner.task import Task, TaskStatus


def test_planner_cannot_be_instantiated() -> None:
    """Planner is a pure interface — no concrete implementation exists yet."""
    with pytest.raises(TypeError):
        Planner()  # type: ignore[abstract]


def test_task_defaults() -> None:
    task = Task(description="Retrieve HR policy documents")
    assert task.status == TaskStatus.PENDING
    assert task.depends_on == []
    assert task.id  # auto-generated


def test_task_dependency_chain() -> None:
    first = Task(description="Fetch documents")
    second = Task(description="Summarize documents", depends_on=[first.id])
    assert second.depends_on == [first.id]


def test_plan_result_defaults() -> None:
    result = PlanResult()
    assert result.status == PlanStatus.PLANNED
    assert result.tasks == []
