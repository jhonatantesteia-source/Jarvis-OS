"""Tool registry for Jarvis OS."""

from __future__ import annotations

from .base import Tool


class ToolRegistry:
    """Registry for tools available to the Jarvis Agent."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool by its unique name."""
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Return a registered tool or None."""
        return self._tools.get(name)

    def list(self) -> tuple[Tool, ...]:
        """Return all registered tools."""
        return tuple(self._tools.values())

    def __contains__(self, name: str) -> bool:
        return name in self._tools