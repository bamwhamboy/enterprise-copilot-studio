"""Tool interface.

Every tool (Knowledge Search today; SQL, REST API, calculator, web
search later) implements this same small contract, so the registry and
the LangGraph tool-use node never need to know about a specific tool's
internals.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolResult(BaseModel):
    """The outcome of executing a tool."""

    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None


class Tool(ABC):
    """Interface every callable tool implements."""

    #: Unique, stable identifier used for registration and by the LLM
    #: when it chooses which tool to call.
    name: str
    #: Human/LLM-readable description of what this tool does and when to use it.
    description: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Run the tool and return a structured result."""
        raise NotImplementedError
