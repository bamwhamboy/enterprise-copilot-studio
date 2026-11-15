"""Response generation with an online grounding and completeness quality gate."""

from __future__ import annotations

import re

from langgraph.config import get_stream_writer

from app.agents.state import ChatState
from app.core.config import Settings
from app.evaluation.response_evaluator import ResponseEvaluator
from app.guardrails.guardrails_runtime import GuardrailsRuntime
from app.llm.gateway import LLMGateway
from app.llm.models import GenerationRequest, LLMMessage
from app.llm.model_registry import resolve_model


_HUMAN_REVIEW_MESSAGE = (
    "I couldn't provide a sufficiently verified answer from the available "
    "company knowledge. The response has been flagged for human review."
)


def _context_text(state: ChatState) -> str:
    chunks = state.get("retrieved_chunks", [])
    return (
        "\n\n".join(
            f"[{i + 1}] ({chunk.citation.document_name}) {chunk.text}"
            for i, chunk in enumerate(chunks)
        )
        or "No relevant context was found."
    )


def _sanitize_llm_output(text: str) -> str:
    """Convert HTML break tags into ordinary newlines."""
    return re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)


def make_response_generator_node(
    settings: Settings,
    gateway: LLMGateway,
    guardrails: GuardrailsRuntime,
    evaluator: ResponseEvaluator,
):
    async def response_generator_node(state: ChatState) -> dict:
        base_messages = state["llm_messages"]
        model = state.get("copilot_model") or None
        provider = resolve_model(model).provider if model else None
        context = _context_text(state)

        max_attempts = max(1, settings.RESPONSE_MAX_EVALUATION_ATTEMPTS)
        attempts = 0
        evaluation_status = "passed"
        last_reasoning = ""
        answer = ""

        while attempts < max_attempts:
            attempts += 1
            messages = base_messages

            if attempts > 1:
                correction_prompt = (
                    "The previous draft answer failed a strict grounding and "
                    "completeness review. Regenerate the answer using ONLY the "
                    "retrieved context. Answer every material part of the user's "
                    "question, including all requested people, dates, dependencies, "
                    "conditions, and other relevant details present in the context. "
                    "Do not omit a requested fact that is available in the context. "
                    "Remove every unsupported claim. If the context does not contain "
                    "enough information to answer part of the question, clearly "
                    "identify that gap instead of inferring or inventing information."
                    "\n\nEvaluator feedback:\n"
                    f"{last_reasoning}"
                )
                messages = [
                    LLMMessage(role="system", content=correction_prompt),
                    *base_messages,
                ]

            request = GenerationRequest(
                messages=messages,
                provider=provider,
                model=model,
                temperature=settings.DEFAULT_TEMPERATURE,
                max_tokens=settings.DEFAULT_MAX_TOKENS,
            )

            answer_parts: list[str] = []
            async for chunk in gateway.stream(request):
                if chunk.delta:
                    answer_parts.append(chunk.delta)

            answer = guardrails.enforce_output(
                _sanitize_llm_output("".join(answer_parts))
            )

            if not settings.RESPONSE_EVALUATION_ENABLED:
                evaluation_status = "disabled"
                break

            try:
                evaluation = await evaluator.evaluate(
                    query=state["user_message"],
                    context=context,
                    answer=answer,
                )
            except Exception as exc:
                evaluation_status = "human_review_required"
                last_reasoning = f"Evaluator unavailable: {exc}"
                answer = _HUMAN_REVIEW_MESSAGE
                break

            last_reasoning = evaluation.reasoning

            if evaluation.passed:
                evaluation_status = "passed" if attempts == 1 else "corrected"
                break

            if attempts >= max_attempts:
                evaluation_status = "human_review_required"
                answer = _HUMAN_REVIEW_MESSAGE
            else:
                evaluation_status = "correcting"

        # Drafts are deliberately buffered until evaluation and any correction
        # attempt are complete. Only the final accepted or safe fallback text
        # is sent to the client.
        writer = get_stream_writer()
        if answer:
            chunk_size = 20
            for i in range(0, len(answer), chunk_size):
                writer({"delta": answer[i:i + chunk_size]})

        return {
            "response_text": answer,
            "evaluation_status": evaluation_status,
            "evaluation_attempts": attempts,
            "evaluation_reasoning": last_reasoning,
            "human_review_required": (
                evaluation_status == "human_review_required"
            ),
            "next_action": None,
            "retrieval_retry_query": None,
        }

    return response_generator_node
