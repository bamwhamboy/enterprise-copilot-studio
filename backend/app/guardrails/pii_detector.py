"""Regex-based PII detection and masking.

Implements the ``PIIDetector`` interface (``app.guardrails.prompt_sanitizer``)
concretely for the common, deterministically-matchable PII categories:
email addresses, phone numbers, US SSNs, and credit-card-shaped numbers.
No AI/ML — pattern matching only, consistent with this codebase's
guardrails so far.

This is deliberately swappable: a future, ML-based PII detector need
only implement the same ``PIIDetector.detect()`` interface to replace
this one, with zero changes to any caller (``GuardrailsRuntime``,
``PromptSanitizer``).
"""

from __future__ import annotations

import re

from app.guardrails.prompt_sanitizer import PIIDetector, PIIMatch

_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone_number": re.compile(r"(?<!\d)(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"),
    "ssn": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    "credit_card": re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)"),
}


class RegexPIIDetector(PIIDetector):
    """Deterministic, regex-based PII detection."""

    def detect(self, text: str) -> list[PIIMatch]:
        matches: list[PIIMatch] = []
        for category, pattern in _PATTERNS.items():
            for m in pattern.finditer(text):
                matches.append(
                    PIIMatch(
                        category=category,
                        matched_text=m.group(0),
                        start=m.start(),
                        end=m.end(),
                    )
                )
        return matches

    def mask(self, text: str) -> str:
        """Replace every detected PII span with a category placeholder.

        Applied to *outgoing* (LLM-generated) text — never to what the
        user typed, which is left intact for the conversation record.
        """
        matches = sorted(self.detect(text), key=lambda m: m.start, reverse=True)
        masked = text
        for match in matches:
            placeholder = f"[REDACTED_{match.category.upper()}]"
            masked = masked[: match.start] + placeholder + masked[match.end :]
        return masked
