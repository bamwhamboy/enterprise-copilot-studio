"""Chat Orchestrator.

The single entry point for all chat interactions (Sprint 5): receives a
user message, loads conversation memory, runs the LangGraph workflow,
persists the turn, and returns a structured, cited response.

Both handle_chat() and handle_chat_stream() drive the exact same
compiled graph -- there is exactly one orchestration pipeline. The only
difference is how each consumes it:

- handle_chat() calls workflow.ainvoke(...) and returns the final state.
- handle_chat_stream() calls workflow.astream(..., stream_mode=["custom",
  "values"]): "custom" events are the token deltas the response
  generator node emits via LangGraph's get_stream_writer() (see
  app/agents/response_generator_node.py); the last "values" event is
  the same final state ainvoke() would have returned. No retrieval,
  prompt-assembly, or generation logic is duplicated here -- all of it
  lives in the graph's nodes, used identically by both paths.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.guardrails.guardrails_runtime import GuardrailsRuntime
from app.memory.conversation_memory_service import ConversationMemoryService
from app.repositories.copilot_repository import CopilotRepository
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent

logger = get_logger(__name__)


class ChatOrchestratorService:
    def __init__(
        self,
        settings: Settings,
        memory: ConversationMemoryService,
        guardrails: GuardrailsRuntime,
        workflow,
        copilot_repository: CopilotRepository,
    ) -> None:
        self._settings = settings
        self._memory = memory
        self._guardrails = guardrails
        self._workflow = workflow
        self._copilots = copilot_repository

    async def _resolve_copilot_and_session(self, request: ChatRequest):
        copilot = await self._copilots.get(request.copilot_id)
        if copilot is None:
            raise NotFoundError("Copilot", request.copilot_id)

        session = await self._memory.get_or_create_session(
            user_id=request.user_id,
            copilot_id=request.copilot_id,
            session_id=request.session_id,
        )
        return copilot, session

    def _resolve_knowledge_source_id(self, request: ChatRequest, copilot) -> str | None:
        if request.knowledge_source_id:
            return str(request.knowledge_source_id)
        if copilot.knowledge_sources:
            # Default to the copilot's first linked source when the caller
            # doesn't specify one -- a reasonable default, not a hard rule.
            return str(copilot.knowledge_sources[0].id)
        return None

    async def _prepare(self, request: ChatRequest):
        """Shared pre-flight for both entry points: validate input, resolve
        the copilot/session, and build the graph's initial state. Not
        "orchestration" itself (that's entirely inside the graph) --
        just the request-to-state translation both paths need identically.
        """
        self._guardrails.enforce_input(request.message)

        copilot, session = await self._resolve_copilot_and_session(request)
        history = await self._memory.load_history(session.id)
        knowledge_source_id = self._resolve_knowledge_source_id(request, copilot)

        initial_state = {
            "user_message": request.message,
            "copilot_name": copilot.name,
            "domain": copilot.domain,
            # The copilot's own model choice, if it has one. Falsy (None or
            # "") falls through to Settings.DEFAULT_LLM_MODEL via the
            # existing `request.model or self.config.default_model` fallback
            # already in app/llm/providers.py -- no change needed there.
            "copilot_model": copilot.model,
            "knowledge_source_id": knowledge_source_id,
            "history": history,
        }
        return session, initial_state

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """Non-streaming chat turn: runs the compiled LangGraph workflow."""
        session, initial_state = await self._prepare(request)

        final_state = await self._workflow.ainvoke(initial_state)

        await self._memory.append_message(session.id, role="user", content=request.message)
        await self._memory.append_message(
            session.id, role="assistant", content=final_state["response_text"]
        )

        return ChatResponse(
            session_id=session.id,
            message=final_state["response_text"],
            citations=final_state.get("citations", []),
            confidence=final_state.get("confidence", 0.0),
        )

    async def handle_chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        """Streaming chat turn: drives the same compiled workflow via astream().

        "custom" stream events (the response generator node's token
        deltas) become SSE "chunk" events as they arrive; once the graph
        finishes, the final "values" event's response_text/citations/
        confidence become the SSE "done" event -- the same
        guardrail-checked, masked text handle_chat() would have returned.
        """
        session, initial_state = await self._prepare(request)

        final_state: dict = {}
        try:
            async for mode, chunk in self._workflow.astream(
                initial_state, stream_mode=["custom", "values"]
            ):
                if mode == "custom":
                    yield ChatStreamEvent(event="chunk", data=chunk)
                elif mode == "values":
                    final_state = chunk
        except Exception as exc:
            logger.error("Streaming generation failed: %s", exc)
            yield ChatStreamEvent(event="error", data={"message": str(exc)})
            return

        response_text = final_state.get("response_text", "")

        await self._memory.append_message(session.id, role="user", content=request.message)
        await self._memory.append_message(session.id, role="assistant", content=response_text)

        citations = [c.model_dump(mode="json") for c in final_state.get("citations", [])]
        yield ChatStreamEvent(
            event="done",
            data={
                "session_id": str(session.id),
                "message": response_text,
                "citations": citations,
                "confidence": final_state.get("confidence", 0.0),
            },
        )
