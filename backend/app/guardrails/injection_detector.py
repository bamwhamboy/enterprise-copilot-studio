"""Regex/pattern-based prompt injection and jailbreak detection.

Implements the ``PromptInjectionDetector`` interface
(``app.guardrails.prompt_sanitizer``) concretely. Covers both prompt
injection ("ignore your instructions") and jailbreak attempts ("DAN
mode", "pretend you have no restrictions") under one detector, since
both are pattern-matchable the same way -- distinguished only by which
reason string gets attached to a match.

No AI/ML -- deterministic phrase matching, same approach as the blocked-
term list already in PromptSanitizer. This is deliberately the
"interface implementation slot" Sprint 4 left open, and is itself
swappable: NVIDIA NeMo Guardrails or another ML-based detector can
replace this class later by implementing the same
PromptInjectionDetector.detect() interface, with zero changes to
GuardrailsRuntime or PromptSanitizer.
"""

from __future__ import annotations

import re

from app.guardrails.prompt_sanitizer import InjectionDetectionResult, PromptInjectionDetector

# (pattern, reason) pairs. Case-insensitive; matched against the whole
# message. Deliberately small and illustrative -- a real deployment would
# maintain this list as configuration, not hardcode it.
_INJECTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"ignore (all )?(previous|prior|above) instructions", re.I), "instruction override attempt"),
    (re.compile(r"disregard (your|the) (system )?(prompt|instructions)", re.I), "instruction override attempt"),
    (re.compile(r"reveal (your|the) system prompt", re.I), "system prompt exfiltration attempt"),
    (re.compile(r"you are now (?!going to answer)", re.I), "role override attempt"),
    (re.compile(r"act as (if you (were|are)|an? unrestricted)", re.I), "role override attempt"),
    (re.compile(r"\bDAN\b|do anything now", re.I), "jailbreak persona attempt"),
    (re.compile(r"pretend you have no (restrictions|rules|guidelines)", re.I), "jailbreak attempt"),
    (re.compile(r"jailbreak", re.I), "explicit jailbreak reference"),
    (re.compile(r"developer mode", re.I), "jailbreak persona attempt"),
    (re.compile(r"bypass (your|all) (safety|content) (filters?|guidelines?)", re.I), "safety bypass attempt"),
]


class RegexPromptInjectionDetector(PromptInjectionDetector):
    """Deterministic, pattern-based injection/jailbreak detection."""

    def detect(self, text: str) -> InjectionDetectionResult:
        reasons = [reason for pattern, reason in _INJECTION_PATTERNS if pattern.search(text)]
        if not reasons:
            return InjectionDetectionResult(is_suspected_injection=False, confidence=0.0)

        # Simple, transparent confidence heuristic: more independent
        # matches -> higher confidence, capped at 1.0. Not a probability
        # in any statistical sense -- a deliberately legible score for a
        # pattern-based detector, not a substitute for a real classifier.
        confidence = min(1.0, 0.5 + 0.15 * len(reasons))
        return InjectionDetectionResult(
            is_suspected_injection=True, confidence=confidence, reasons=reasons
        )
