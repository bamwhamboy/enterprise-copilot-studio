"""Dedicated LLM scorer for answer completeness."""

from __future__ import annotations

import json
from typing import Any

import weave
from pydantic import BaseModel, ConfigDict

from weave.scorers import LLMScorer


class CompletenessResponse(BaseModel):
    """Structured result returned by the completeness evaluator."""

    model_config = ConfigDict(extra="forbid", strict=True)

    complete: bool
    missing_information: list[str]
    reasoning: str


class CompletenessScorer(LLMScorer):
    """Evaluate whether an answer covers all material parts of a question."""

    system_prompt: str = (
        "You are a strict enterprise RAG answer-completeness evaluator. "
        "Evaluate coverage, not factual grounding or writing style. "
        "Identify every material part of the user's question. "
        "Compare the question, retrieved context, and candidate answer. "
        "If the context contains a requested fact that the answer omits, "
        "the answer is incomplete. Check names, dates, deadlines, "
        "dependencies, conditions, and every part of multi-part questions. "
        "Do not require facts genuinely absent from the context when the "
        "answer clearly states that they are unavailable. "
        "Never infer facts. Return only valid JSON with exactly these keys: "
        "complete (boolean), missing_information (array of strings), "
        "reasoning (string). If information is missing, complete must be "
        "false and missing_information must identify each omission. "
        "If coverage is complete, complete must be true and "
        "missing_information must be an empty array."
    )

    user_prompt: str = (
        "Question and retrieved context:\n{context}\n\n"
        "Candidate answer:\n{output}\n\n"
        "Evaluate whether every material, answerable part of the question "
        "is covered by the candidate answer."
    )

    temperature: float = 0.0
    max_tokens: int = 1024

    @weave.op
    async def score(self, *, output: str, context: str, **kwargs: Any) -> dict:
        """Return a validated completeness result."""

        response = await self._acompletion(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": self.user_prompt.format(
                        context=context,
                        output=output,
                    ),
                },
            ],
            model=self.model_id,
            response_format={"type": "json_object"},
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Completeness evaluator returned an empty response")

        result = CompletenessResponse.model_validate(json.loads(content))

        if result.complete and result.missing_information:
            raise ValueError(
                "Completeness evaluator returned contradictory results"
            )

        if not result.complete and not result.missing_information:
            raise ValueError(
                "Completeness evaluator marked the answer incomplete "
                "without identifying missing information"
            )

        return result.model_dump()
