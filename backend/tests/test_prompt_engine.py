"""Tests for app.prompt_engine — real string-rendering logic, no AI."""

import pytest

from app.prompt_engine.renderer import MissingPromptVariableError, PromptRenderer
from app.prompt_engine.templates import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    PromptTemplate,
)


def test_render_single_template() -> None:
    renderer = PromptRenderer()
    result = renderer.render(DEFAULT_USER_PROMPT, {"question": "What is our leave policy?"})
    assert result == "What is our leave policy?"


def test_render_missing_variable_raises() -> None:
    renderer = PromptRenderer()
    with pytest.raises(MissingPromptVariableError) as exc_info:
        renderer.render(DEFAULT_SYSTEM_PROMPT, {"copilot_name": "HR Copilot"})
    assert "domain" in exc_info.value.missing
    assert "company_name" in exc_info.value.missing


def test_render_conversation_produces_ordered_messages() -> None:
    renderer = PromptRenderer()
    variables = {
        "copilot_name": "HR Copilot",
        "domain": "HR",
        "company_name": "Enterprise Copilot Studio",
        "question": "How many vacation days do I get?",
    }
    messages = renderer.render_conversation([DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT], variables)

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert "HR Copilot" in messages[0].content
    assert messages[1].role == "user"
    assert messages[1].content == "How many vacation days do I get?"


def test_custom_template_variable_deduplication() -> None:
    template = PromptTemplate(
        name="dup_test",
        role="user",
        template="{a} {a} {b}",
        variables=["a", "a", "b"],
    )
    assert template.variables == ["a", "b"]
