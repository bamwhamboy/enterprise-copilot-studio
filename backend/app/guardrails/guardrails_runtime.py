"""Guardrails runtime.

Wires the Sprint 4 guardrails interfaces plus Sprint 5's concrete
implementations into the two checkpoints every chat turn passes
through: ``enforce_input()`` before the LLM sees the user's message,
and ``enforce_output()`` after the LLM responds, before the caller
sees it.

Depends only on the ``InputValidator``/``OutputValidator`` interfaces
plus PII masking — swapping in NVIDIA NeMo Guardrails (or any other
framework) later means implementing those same interfaces and passing
them in here; no changes to this class or any caller
(``ChatOrchestratorService``) required.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.guardrails.pii_detector import RegexPIIDetector
from app.guardrails.prompt_sanitizer import PromptSanitizer
from app.guardrails.validator import OutputValidator, ValidationResult

logger = get_logger(__name__)


class GuardrailViolationError(Exception):
    """Raised when input or output fails a BLOCKING guardrail check."""

    def __init__(self, stage: str, result: ValidationResult) -> None:
        self.stage = stage
        self.result = result
        reasons = "; ".join(issue.message for issue in result.issues)
        super().__init__(f"Guardrail violation at {stage}: {reasons}")


class GuardrailsRuntime:
    """Central guardrails checkpoint used by the chat orchestrator."""

    def __init__(
        self,
        settings: Settings,
        input_validator: PromptSanitizer,
        output_validator: OutputValidator,
        pii_detector: RegexPIIDetector,
    ) -> None:
        self._settings = settings
        self._input_validator = input_validator
        self._output_validator = output_validator
        self._pii_detector = pii_detector

    def validate_input(self, text: str) -> ValidationResult:
        if not self._settings.GUARDRAILS_INPUT_ENABLED:
            return ValidationResult(is_valid=True)
        result = self._input_validator.validate(text)
        if not result.is_valid:
            logger.warning(
                "Input guardrail blocked message: %s", [i.message for i in result.issues]
            )
        return result

    def validate_output(self, text: str) -> ValidationResult:
        if not self._settings.GUARDRAILS_OUTPUT_ENABLED:
            return ValidationResult(is_valid=True)
        result = self._output_validator.validate(text)
        if not result.is_valid:
            logger.warning(
                "Output guardrail blocked response: %s", [i.message for i in result.issues]
            )
        return result

    def mask_pii(self, text: str) -> str:
        if not self._settings.GUARDRAILS_PII_MASKING_ENABLED:
            return text
        return self._pii_detector.mask(text)

    def enforce_input(self, text: str) -> None:
        """Validate input; raise ``GuardrailViolationError`` if blocked."""
        result = self.validate_input(text)
        if not result.is_valid:
            raise GuardrailViolationError("input", result)

    def enforce_output(self, text: str) -> str:
        """Validate + mask output.

        Raises if blocked; otherwise returns the (possibly PII-masked) text.
        """
        result = self.validate_output(text)
        if not result.is_valid:
            raise GuardrailViolationError("output", result)
        return self.mask_pii(text)
