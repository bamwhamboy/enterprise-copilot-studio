"""Response generation with an online quality gate.

The node generates a draft, evaluates it against the retrieved RAG context
with the Weave LLM judge, and gives the generation model one opportunity to
correct unsupported claims. A second failed evaluation quarantines the
answer for human review. Only the final verified answer is emitted to the
stream, so an unverified draft is never exposed to the client.
"""

from __future__ import annotations

from langgraph.config import get_stream_writer

from app.agents.state import ChatState
from app.core.config import Settings
from app.evaluation.response_evaluator import ResponseEvaluator
from app.guardrails.guardrails_runtime import GuardrailsRuntime
from app.llm.gateway import LLMGateway
from app.llm.models import GenerationRequest, LLMMessage

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


def make_response_generator_node(
    settings: Settings,
    gateway: LLMGateway,
    guardrails: GuardrailsRuntime,
    evaluator: ResponseEvaluator,
):
    async def response_generator_node(state: ChatState) -> dict:
        base_messages = state["llm_messages"]
        model = state.get("copilot_model") or None
        context = _context_text(state)
        attempts = 0
        evaluation_status = "passed"
        last_reasoning = ""
        answer = ""

        while attempts < max(1, settings.RESPONSE_MAX_EVALUATION_ATTEMPTS):
            attempts += 1

            messages = base_messages
            if attempts > 1:
                correction_prompt = (
                    "The previous draft answer failed a strict grounding review. "
                    "Regenerate the answer using ONLY the retrieved context. "
                    "Remove every unsupported claim. If the context does not "
                    "contain enough information to answer the question, say so "
                    "explicitly instead of inferring.\n\n"
                    f"Evaluator feedback:\n{last_reasoning}"
                )
                messages = [LLMMessage(role="system", content=correction_prompt), *base_messages]

            request = GenerationRequest(
                messages=messages,
                model=model,
                temperature=settings.DEFAULT_TEMPERATURE,
                max_tokens=settings.DEFAULT_MAX_TOKENS,
            )
            generation = await gateway.generate(request)
            answer = guardrails.enforce_output(generation.content)

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
                # A missing evaluator is a safety failure, not a reason to
                # silently serve an unchecked financial answer.
                evaluation_status = "human_review_required"
                last_reasoning = f"Evaluator unavailable: {exc}"
                answer = _HUMAN_REVIEW_MESSAGE
                break

            last_reasoning = evaluation.reasoning
            if evaluation.passed:
                evaluation_status = "passed" if attempts == 1 else "corrected"
                break

            evaluation_status = "correcting"

            if attempts >= settings.RESPONSE_MAX_EVALUATION_ATTEMPTS:
                evaluation_status = "human_review_required"
                answer = _HUMAN_REVIEW_MESSAGE

        writer = get_stream_writer()
        if answer:
            # Emit only after the final quality gate. This deliberately sends
            # the verified response as one SSE chunk rather than leaking the
            # first draft before evaluation completes.
            writer({"delta": answer})

        return {
            "response_text": answer,
            "evaluation_status": evaluation_status,
            "evaluation_attempts": attempts,
            "evaluation_reasoning": last_reasoning,
            "human_review_required": evaluation_status == "human_review_required",
        }

    return response_generator_node
