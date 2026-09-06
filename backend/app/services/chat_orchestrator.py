"""Chat Orchestrator.

The single entry point for all chat interactions: receives a user message,
loads conversation memory, runs the LangGraph workflow, persists the turn,
and returns a structured, cited response.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.guardrails.guardrails_runtime import GuardrailsRuntime
from app.memory.conversation_memory_service import ConversationMemoryService
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent
from app.services.copilot_service import CopilotService
from app.services.document_service import DocumentService

logger = get_logger(__name__)


class ChatOrchestratorService:
    def __init__(
        self,
        settings: Settings,
        memory: ConversationMemoryService,
        guardrails: GuardrailsRuntime,
        workflow,
        copilot_service: CopilotService,
        document_service: DocumentService,
    ) -> None:
        self._settings = settings
        self._memory = memory
        self._guardrails = guardrails
        self._workflow = workflow
        self._copilots = copilot_service
        self._documents = document_service

    async def _resolve_copilot_and_session(self, request: ChatRequest):
        copilot = await self._copilots.get_copilot(
            request.copilot_id, organization_id=request.organization_id
        )
        session = await self._memory.get_or_create_session(
            user_id=request.user_id,
            copilot_id=request.copilot_id,
            session_id=request.session_id,
        )
        return copilot, session

    def _resolve_knowledge_source_id(self, request: ChatRequest, copilot) -> str | None:
        copilot_source_ids = {str(ks.id) for ks in copilot.knowledge_sources}
        if request.knowledge_source_id:
            requested = str(request.knowledge_source_id)
            if requested not in copilot_source_ids:
                raise NotFoundError("KnowledgeSource", request.knowledge_source_id)
            return requested
        if copilot.knowledge_sources:
            return str(copilot.knowledge_sources[0].id)
        return None

    async def _resolve_scope(
        self,
        request: ChatRequest,
        copilot,
    ) -> tuple[str | None, str | None]:
        """Resolve and validate knowledge-source/document retrieval scope."""

        if request.document_id is None:
            return self._resolve_knowledge_source_id(request, copilot), None

        document = await self._documents.get_document(
            request.document_id,
            organization_id=request.organization_id,
        )

        document_knowledge_source_id = str(document.knowledge_source_id)

        copilot_source_ids = {
            str(ks.id) for ks in copilot.knowledge_sources
        }

        if document_knowledge_source_id not in copilot_source_ids:
            raise NotFoundError("Document", request.document_id)

        if (
            request.knowledge_source_id is not None
            and str(request.knowledge_source_id)
            != document_knowledge_source_id
        ):
            raise NotFoundError("Document", request.document_id)

        return document_knowledge_source_id, str(request.document_id)

    async def _prepare(self, request: ChatRequest):
        self._guardrails.enforce_input(request.message)
        copilot, session = await self._resolve_copilot_and_session(request)
        history = await self._memory.load_history(session.id)
        knowledge_source_id, document_id = await self._resolve_scope(
            request, copilot
        )

        initial_state = {
            "user_message": request.message,
            "copilot_name": copilot.name,
            "domain": copilot.domain,
            "copilot_model": copilot.model,
            "knowledge_source_id": knowledge_source_id,
            "document_id": document_id,
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
            evaluation_status=final_state.get("evaluation_status", "passed"),
            evaluation_attempts=final_state.get("evaluation_attempts", 0),
            human_review_required=final_state.get("human_review_required", False),
        )

    async def handle_chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        """Streaming chat turn using the same verified final state.

        The response generator emits a single custom event only after the
        evaluation/correction loop completes, so an unverified draft is never
        sent to the browser.
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
                "evaluation_status": final_state.get("evaluation_status", "passed"),
                "evaluation_attempts": final_state.get("evaluation_attempts", 0),
                "human_review_required": final_state.get("human_review_required", False),
            },
        )
