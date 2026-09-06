"""Online response evaluation and hallucination guardrail.

This module uses W&B Weave's LLM-powered HallucinationFreeScorer as an
online judge. The scorer checks the generated answer against the retrieved
RAG context before the answer is exposed to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass

import weave
from weave.scorers import HallucinationFreeScorer

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ResponseEvaluation:
    passed: bool
    has_hallucination: bool
    reasoning: str


class ResponseEvaluator:
    """Run an LLM judge against a generated RAG response."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._enabled = settings.RESPONSE_EVALUATION_ENABLED
        self._scorer: HallucinationFreeScorer | None = None

        if not self._enabled:
            return

        if settings.WANDB_API_KEY:
            try:
                weave.init(
                    settings.WEAVE_PROJECT,
                    settings={"print_call_link": False},
                )
            except Exception:
                # Evaluation itself can still run through the scorer if
                # Weave tracing cannot initialize. Do not make telemetry
                # availability the only thing deciding whether an answer
                # is checked.
                logger.exception("Failed to initialize Weave tracing")

        try:
            self._scorer = HallucinationFreeScorer(
                model_id=settings.RESPONSE_EVALUATOR_MODEL,
                system_prompt=(
                    "You are a strict enterprise RAG answer evaluator. "
                    "An answer is acceptable only when every material factual "
                    "claim is supported by the supplied context. Treat any "
                    "invented policy rule, amount, date, threshold, exception, "
                    "eligibility condition, or other unsupported detail as a "
                    "hallucination. If the context does not answer the question, "
                    "the correct behavior is to say that the information is not "
                    "available rather than infer or invent it."
                ),
                user_prompt=(
                    "Question:\n{query}\n\n"
                    "Retrieved context:\n{context}\n\n"
                    "Candidate answer:\n{output}\n\n"
                    "Determine whether the candidate answer is fully grounded "
                    "in the retrieved context. Be strict."
                ),
            )
        except Exception:
            logger.exception("Failed to initialize Weave response scorer")
            self._scorer = None

    @weave.op()
    async def evaluate(
        self,
        query: str,
        context: str,
        answer: str,
    ) -> ResponseEvaluation:
        """Evaluate one generated answer against the retrieved context."""
        if not self._enabled:
            return ResponseEvaluation(
                passed=True,
                has_hallucination=False,
                reasoning="Response evaluation is disabled.",
            )

        if self._scorer is None:
            raise RuntimeError("Response evaluator is not available")

        result = await self._scorer.score(
            query=query,
            context=context,
            output=answer,
        )

        has_hallucination = bool(result.get("has_hallucination", True))
        reasoning = str(
            result.get("reasonings")
            or result.get("reasoning")
            or result.get("explanation")
            or "The evaluator flagged the response as unsupported."
        )

        return ResponseEvaluation(
            passed=not has_hallucination,
            has_hallucination=has_hallucination,
            reasoning=reasoning,
        )
