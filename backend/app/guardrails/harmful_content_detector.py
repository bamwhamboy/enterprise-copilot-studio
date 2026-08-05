"""Harmful content detection for outgoing (LLM-generated) text.

Implements the OutputValidator interface (app.guardrails.validator).
Keyword/pattern-based, same rule-based approach as the rest of this
codebase's guardrails -- flags categories of clearly harmful content
(self-harm instructions, weapons/explosives instructions, illegal
activity facilitation) as BLOCKING findings.

Deliberately conservative and narrow: this is a last-line safety net
over model output, not a substitute for provider-side safety training.
Swappable later for NeMo Guardrails or a moderation-model-backed
validator via the same OutputValidator interface.
"""

from __future__ import annotations

import re

from app.guardrails.validator import (
    OutputValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

_HARMFUL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"how to (make|build|synthesize) (a bomb|explosives?)", re.I), "explosives instructions"),
    (re.compile(r"step[- ]by[- ]step.*(suicide|self-harm)", re.I), "self-harm instructions"),
    (re.compile(r"how to (make|synthesize) (meth|ricin|sarin|nerve gas)", re.I), "weapon/drug synthesis instructions"),
]


class HarmfulContentValidator(OutputValidator):
    """Deterministic, pattern-based harmful-content detection for LLM output."""

    def validate(self, text: str, *, context: dict[str, str] | None = None) -> ValidationResult:
        issues = [
            ValidationIssue(
                code="harmful_content",
                message=f"Response flagged for possible {reason}.",
                severity=ValidationSeverity.BLOCKING,
            )
            for pattern, reason in _HARMFUL_PATTERNS
            if pattern.search(text)
        ]
        return ValidationResult(is_valid=not issues, issues=issues)
