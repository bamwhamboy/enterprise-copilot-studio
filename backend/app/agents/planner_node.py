"""Planner node.

Decides the workflow for a chat turn. SimpleChatPlanner is the first
concrete implementation of the Planner interface Sprint 4 established
(app.planner.planner) -- it always plans a "retrieve, then respond"
task sequence today, but the interface leaves room for a future
planner to choose between retrieval, tool calls, or a direct response
based on the message, without changing anything downstream.
"""

from __future__ import annotations

from app.agents.state import ChatState
from app.planner.planner import PlanResult, PlanStatus, Planner
from app.planner.task import Task, TaskStatus


class SimpleChatPlanner(Planner):
    """A minimal, deterministic Planner: always retrieve, then respond."""

    async def plan(self, goal: str, context: dict[str, str] | None = None) -> list[Task]:
        retrieve_task = Task(description=f"Retrieve knowledge relevant to: {goal}")
        respond_task = Task(
            description="Generate a grounded response using retrieved context",
            depends_on=[retrieve_task.id],
        )
        return [retrieve_task, respond_task]

    async def execute(self, tasks: list[Task]) -> PlanResult:
        # Execution itself happens via the rest of the LangGraph workflow
        # (retrieval_node, response_generator_node) -- this satisfies the
        # Planner interface's contract and marks tasks completed once the
        # graph has run them.
        for task in tasks:
            task.status = TaskStatus.COMPLETED
        return PlanResult(tasks=tasks, status=PlanStatus.COMPLETED)


async def planner_node(state: ChatState) -> dict:
    planner = SimpleChatPlanner()
    plan = await planner.plan(state["user_message"])
    return {"plan": plan}
