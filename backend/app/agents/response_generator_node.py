"""Response generator node.

Calls the LLM Gateway (Sprint 4/5) with the assembled messages, then
runs the output through the Guardrails runtime (validation + PII
masking) before it becomes part of state.

Always streams internally (gateway.stream(), not gateway.generate()),
emitting each delta via LangGraph's get_stream_writer(). This is what
makes a single node implementation serve both entry points:

- POST /chat calls workflow.ainvoke(...) -- get_stream_writer() is a
  no-op when nobody's consuming the graph's custom stream, so this
  behaves exactly like a non-streaming call: the full accumulated,
  guardrail-checked text lands in state["response_text"].
- POST /chat/stream calls workflow.astream(..., stream_mode=["custom",
  "values"]) -- the exact same deltas emitted here are what the
  orchestrator forwards to the client as SSE "chunk" events, and the
  final "values" event carries the same guardrail-checked
  state["response_text"] used for the "done" event.

No other node, and no orchestrator code, duplicates this call or the
guardrail enforcement -- there is exactly one place a response is
generated.
"""

from __future__ import annotations

from langgraph.config import get_stream_writer

from app.agents.state import ChatState
from app.core.config import Settings
from app.guardrails.guardrails_runtime import GuardrailsRuntime
from app.llm.gateway import LLMGateway
from app.llm.models import GenerationRequest


def make_response_generator_node(
    settings: Settings, gateway: LLMGateway, guardrails: GuardrailsRuntime
):
    async def response_generator_node(state: ChatState) -> dict:
        request = GenerationRequest(
            messages=state["llm_messages"],
            temperature=settings.DEFAULT_TEMPERATURE,
            max_tokens=settings.DEFAULT_MAX_TOKENS,
        )

        writer = get_stream_writer()
        accumulated = ""
        async for chunk in gateway.stream(request):
            if chunk.delta:
                accumulated += chunk.delta
                writer({"delta": chunk.delta})

        safe_text = guardrails.enforce_output(accumulated)
        return {"response_text": safe_text}

    return response_generator_node
