"""Provider-agnostic LLM interface for Jarvis OS.

This module intentionally contains no concrete provider implementation and no
external API dependency. Concrete providers can be added in later milestones.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Normalized response returned by an LLM provider."""

    content: str
    model: str | None = None
    tool_calls: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    raw: Any = None


class LLMProvider(ABC):
    """Minimal contract consumed by Jarvis Agent/Orchestrator layers."""

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether the provider supports structured tool/function calls."""
        raise NotImplementedError

    @abstractmethod
    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a normalized response from a sequence of messages."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Return whether the provider is currently usable."""
        raise NotImplementedError