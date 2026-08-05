"""Chat endpoints — the single entry point for all chat interactions.

``POST /chat`` runs the full LangGraph workflow and returns a complete
response. ``POST /chat/stream`` streams the response token-by-token via
Server-Sent Events, for a future frontend to render progressively.
"""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.dependencies import ChatOrchestratorServiceDep
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse, summary="Send a chat message")
async def chat(payload: ChatRequest, service: ChatOrchestratorServiceDep) -> ChatResponse:
    return await service.handle_chat(payload)


@router.post("/stream", summary="Send a chat message and stream the response (SSE)")
async def chat_stream(payload: ChatRequest, service: ChatOrchestratorServiceDep) -> StreamingResponse:
    async def event_source():
        async for event in service.handle_chat_stream(payload):
            yield f"event: {event.event}\ndata: {json.dumps(event.data)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
