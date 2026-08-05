"""Reusable validation framework.

Defines the shared vocabulary (``ValidationSeverity``, ``ValidationResult``)
and the two core interfaces — ``InputValidator`` and ``OutputValidator`` —
that any concrete guardrail (prompt sanitization, PII detection, policy
checks, output-format checks, ...) implements. No AI logic here; this
is pure structure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """How serious a validation finding is."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class ValidationIssue(BaseModel):
    """A single finding raised by a validator."""

    code: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.WARNING


class ValidationResult(BaseModel):
    """The outcome of running one or more validators over some text."""

    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def has_blocking_issues(self) -> bool:
        return any(issue.severity == ValidationSeverity.BLOCKING for issue in self.issues)


class InputValidator(ABC):
    """Validates text before it reaches an LLM (a user prompt, for example)."""

    @abstractmethod
    def validate(self, text: str, *, context: dict[str, str] | None = None) -> ValidationResult:
        raise NotImplementedError


class OutputValidator(ABC):
    """Validates text produced by an LLM before it reaches the caller."""

    @abstractmethod
    def validate(self, text: str, *, context: dict[str, str] | None = None) -> ValidationResult:
        raise NotImplementedError
