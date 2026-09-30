"""Tool abstractions for Jarvis OS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Normalized result returned by a Tool."""

    success: bool
    content: Any = None
    error: str | None = None


class Tool(ABC):
    """Minimal contract for tools exposed to the Jarvis Agent."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the tool."""
        raise NotImplementedError

    @property
    @abstractmethod
    def input_schema(self) -> Mapping[str, Any]:
        """Schema describing the tool input."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        raise NotImplementedError