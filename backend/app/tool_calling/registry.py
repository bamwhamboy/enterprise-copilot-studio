"""Tool registry.

A simple name -> Tool map. New tools register themselves here (or are
registered by the DI provider that constructs them); nothing else in
the codebase needs to change to add a tool.
"""

from __future__ import annotations

from app.tool_calling.base import Tool, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    async def execute(self, name: str, **kwargs) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(tool_name=name, success=False, error=f"Unknown tool: '{name}'")
        try:
            return await tool.execute(**kwargs)
        except Exception as exc:  # a tool's own bug should never crash the chat turn
            return ToolResult(tool_name=name, success=False, error=str(exc))
