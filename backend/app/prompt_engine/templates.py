"""Prompt templates.

A ``PromptTemplate`` pairs a role (system / developer / user) with a
``str.format``-style template string and the variable names it expects.
Rendering happens in ``renderer.py``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.llm.models import MessageRole


class PromptTemplate(BaseModel):
    """A single named, role-scoped prompt template."""

    name: str
    role: MessageRole
    template: str
    variables: list[str] = Field(default_factory=list)
    description: str | None = None

    @field_validator("variables")
    @classmethod
    def _dedupe_preserving_order(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for item in value:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped


# --- A small built-in library, illustrating each supported role -----------
# Real, domain-specific templates (per copilot) are expected to be added
# alongside this library in a later sprint — these establish the pattern.

DEFAULT_SYSTEM_PROMPT = PromptTemplate(
    name="default_system",
    role="system",
    template=(
        "You are {copilot_name}, an enterprise AI assistant for the "
        "{domain} domain at {company_name}. Answer using only the "
        "provided knowledge sources. If you don't know, say so."
    ),
    variables=["copilot_name", "domain", "company_name"],
    description="Baseline system prompt for a domain-scoped enterprise copilot.",
)

DEFAULT_DEVELOPER_PROMPT = PromptTemplate(
    name="default_developer",
    role="developer",
    template=(
        "Response format: {response_format}. Maximum length: {max_length} "
        "words. Always cite sources by document name."
    ),
    variables=["response_format", "max_length"],
    description="Baseline developer prompt controlling output format/constraints.",
)

DEFAULT_USER_PROMPT = PromptTemplate(
    name="default_user",
    role="user",
    template="{question}",
    variables=["question"],
    description="Passthrough template for the end user's raw question.",
)

BUILTIN_TEMPLATES: dict[str, PromptTemplate] = {
    template.name: template
    for template in (DEFAULT_SYSTEM_PROMPT, DEFAULT_DEVELOPER_PROMPT, DEFAULT_USER_PROMPT)
}
