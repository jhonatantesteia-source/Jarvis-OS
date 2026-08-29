"""Provider-agnostic LLM interface for Jarvis OS.

This module intentionally contains no concrete provider implementation and no
external API dependency. Concrete providers can be added in later milestones.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from core.llm.models import LLMRequest, LLMResponse

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
        request: LLMRequest,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a normalized response from an LLM request."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Return whether the provider is currently usable."""
        raise NotImplementedError