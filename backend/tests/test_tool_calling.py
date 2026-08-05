"""Tests for the tool calling framework (Sprint 5)."""

import pytest

from app.tool_calling.base import Tool, ToolResult
from app.tool_calling.registry import ToolRegistry


class _EchoTool(Tool):
    name = "echo"
    description = "Echoes back its input."

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(tool_name=self.name, success=True, output=kwargs)


class _BrokenTool(Tool):
    name = "broken"
    description = "Always raises."

    async def execute(self, **kwargs) -> ToolResult:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_registry_executes_registered_tool() -> None:
    registry = ToolRegistry()
    registry.register(_EchoTool())

    result = await registry.execute("echo", message="hi")

    assert result.success is True
    assert result.output == {"message": "hi"}


@pytest.mark.asyncio
async def test_registry_returns_error_for_unknown_tool() -> None:
    registry = ToolRegistry()
    result = await registry.execute("nonexistent")
    assert result.success is False
    assert "Unknown tool" in result.error


@pytest.mark.asyncio
async def test_registry_catches_tool_exceptions() -> None:
    registry = ToolRegistry()
    registry.register(_BrokenTool())

    result = await registry.execute("broken")

    assert result.success is False
    assert "boom" in result.error


def test_list_tools_returns_all_registered() -> None:
    registry = ToolRegistry()
    registry.register(_EchoTool())
    registry.register(_BrokenTool())

    names = {tool.name for tool in registry.list_tools()}
    assert names == {"echo", "broken"}
