
"""Online response evaluation and completeness guardrail."""

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
    """Evaluate grounding and completeness independently."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.RESPONSE_EVALUATION_ENABLED
        self._scorer: HallucinationFreeScorer | None = None
        self._completeness_scorer: HallucinationFreeScorer | None = None

        if not self._enabled:
            return

        if settings.WANDB_API_KEY:
            try:
                weave.init(
                    settings.WEAVE_PROJECT,
                    settings={"print_call_link": False},
                )
            except Exception:
                logger.exception("Failed to initialize Weave tracing")

        try:
            self._scorer = HallucinationFreeScorer(
                model_id=settings.RESPONSE_EVALUATOR_MODEL,
                system_prompt=(
                    "You are a strict enterprise RAG grounding evaluator. "
                    "Flag factual claims in the answer that are not supported "
                    "by the supplied context. Do not assess completeness; "
                    "another evaluator handles that."
                ),
                user_prompt=(
                    "Context:\n{input_data}\n\n"
                    "Answer:\n{output}\n\n"
                    "Determine whether the answer contains unsupported factual "
                    "claims. Return the scorer's normal result."
                ),
            )

            self._completeness_scorer = HallucinationFreeScorer(
                model_id=settings.RESPONSE_EVALUATOR_MODEL,
                system_prompt=(
                    "You are a strict enterprise RAG answer-completeness evaluator. "
                    "Ignore writing style and evaluate coverage only. Identify every "
                    "material part of the user's question. Compare each requested "
                    "part with the retrieved context and candidate answer. Flag an "
                    "answer as incomplete if the context contains a requested fact "
                    "that the answer omits. This includes names, dates, deadlines, "
                    "dependencies, conditions, and each part of multi-part questions. "
                    "Do not require facts that are genuinely absent from the context "
                    "when the answer clearly states that they are unavailable. "
                    "Do not infer facts or treat an unsupported guess as coverage."
                ),
                user_prompt=(
                    "Question and retrieved context:\n{input_data}\n\n"
                    "Candidate answer:\n{output}\n\n"
                    "Is every material, answerable part of the question covered? "
                    "Flag missing requested information as a failure, even when "
                    "the included statements are factually correct. Explain which "
                    "parts are missing or confirm that coverage is complete."
                ),
            )
        except Exception:
            logger.exception("Failed to initialize response evaluation scorers")
            self._scorer = None
            self._completeness_scorer = None

    @weave.op()
    async def evaluate(
        self,
        query: str,
        context: str,
        answer: str,
    ) -> ResponseEvaluation:
        """Check grounding and coverage before accepting an answer."""
        if not self._enabled:
            return ResponseEvaluation(
                passed=True,
                has_hallucination=False,
                reasoning="Response evaluation is disabled.",
            )

        if self._scorer is None or self._completeness_scorer is None:
            raise RuntimeError("Response evaluator is not available")

        evaluation_context = (
            f"Question:\n{query}\n\nRetrieved context:\n{context}"
        )

        grounding_result = await self._scorer.score(
            context=evaluation_context,
            output=answer,
        )
        print("GROUNDING SCORER RESULT:", repr(grounding_result))
        completeness_result = await self._completeness_scorer.score(
            context=evaluation_context,
            output=answer,
        )
        print("COMPLETENESS_SCORER RESULT:", repr(completeness_result))
        grounding_failed = bool(
            grounding_result.get("has_hallucination", True)
        )

        completeness_failed = bool(
            completeness_result.get("has_hallucination", True)
        )

        completeness_details = completeness_result.get("reasonings", [])
        if isinstance(completeness_details, list):
            completeness_failed = completeness_failed or any(
                isinstance(item, dict)
                and str(item.get("hallucination_type", "")).strip().lower()
                in {"missing information", "omission", "incomplete answer"}
                for item in completeness_details
            )

        grounding_reason = str(
            grounding_result.get("reasonings")
            or grounding_result.get("reasoning")
            or grounding_result.get("explanation")
            or "Grounding evaluator returned no explanation."
        )
        completeness_reason = str(
            completeness_result.get("reasonings")
            or completeness_result.get("reasoning")
            or completeness_result.get("explanation")
            or "Completeness evaluator returned no explanation."
        )

        failures = []
        if grounding_failed:
            failures.append(f"Grounding failure: {grounding_reason}")
        if completeness_failed:
            failures.append(f"Completeness failure: {completeness_reason}")

        return ResponseEvaluation(
            passed=not failures,
            has_hallucination=grounding_failed or completeness_failed,
            reasoning=(
                " ".join(failures)
                if failures
                else grounding_reason
            ),
        )
