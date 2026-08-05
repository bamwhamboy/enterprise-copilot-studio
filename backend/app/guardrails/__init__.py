"""Guardrails: reusable validation framework.

Sprint 4 implements: ``validator.py`` (the ``InputValidator``/
``OutputValidator`` interfaces and shared ``ValidationResult`` shape)
and ``prompt_sanitizer.py`` (real, rule-based blocked-prompt detection,
plus ``PromptInjectionDetector``/``PIIDetector`` interfaces for later
sprints to implement and inject).

No AI logic — blocked-term matching is deterministic string matching.
"""
