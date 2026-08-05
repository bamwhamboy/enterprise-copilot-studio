"""Prompt rendering.

Renders a ``PromptTemplate`` — or an ordered sequence of them — with a
variables dict into plain strings / ``LLMMessage`` objects ready for the
(future) LLM Gateway. Pure string substitution; no AI logic.
"""

from __future__ import annotations

from app.llm.models import LLMMessage
from app.prompt_engine.templates import PromptTemplate


class MissingPromptVariableError(Exception):
    """Raised when a template's required variables aren't all supplied."""

    def __init__(self, template_name: str, missing: list[str]) -> None:
        self.template_name = template_name
        self.missing = missing
        super().__init__(
            f"Template '{template_name}' is missing variables: {', '.join(missing)}"
        )


class PromptRenderer:
    """Renders prompt templates into strings and message sequences."""

    def render(self, template: PromptTemplate, variables: dict[str, str]) -> str:
        """Render a single template. Raises if a required variable is missing."""
        missing = [name for name in template.variables if name not in variables]
        if missing:
            raise MissingPromptVariableError(template.name, missing)

        try:
            return template.template.format(**variables)
        except KeyError as exc:
            # Referenced in the template text but not declared in
            # template.variables — an authoring error, not a caller error.
            raise MissingPromptVariableError(template.name, [str(exc).strip("'")]) from exc

    def render_conversation(
        self, templates: list[PromptTemplate], variables: dict[str, str]
    ) -> list[LLMMessage]:
        """Render an ordered sequence of templates into ready-to-send messages.

        Typical usage: ``[system_template, developer_template, user_template]``
        rendered together into the message list a ``GenerationRequest`` expects.
        """
        return [
            LLMMessage(role=template.role, content=self.render(template, variables))
            for template in templates
        ]
