"""Shared state passed between LangGraph workflow nodes.

A plain TypedDict (not a Pydantic model): LangGraph merges each node's
returned partial dict into this state using simple last-write-wins
semantics, which is exactly right for this sprint's linear pipeline --
no custom reducers needed.
"""

from __future__ import annotations

from typing import TypedDict

from app.knowledge_engine.models import Citation, RetrievedChunk
from app.llm.models import LLMMessage
from app.planner.task import Task


class ChatState(TypedDict, total=False):
    # --- inputs, set before the graph runs ---
    user_message: str
    copilot_name: str
    domain: str
    copilot_model: str | None
    knowledge_source_id: str | None
    history: list[LLMMessage]

    # --- planner node output ---
    plan: list[Task]

    # --- retrieval node output ---
    retrieved_chunks: list[RetrievedChunk]
    confidence: float

    # --- context builder node output ---
    llm_messages: list[LLMMessage]

    # --- response generator node output ---
    response_text: str

    # --- citation builder node output ---
    citations: list[Citation]
