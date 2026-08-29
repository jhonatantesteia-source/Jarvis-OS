"""Deterministic fake LLM provider for testing and development.

This provider requires no API keys and performs no network requests,
returning deterministic responses based on the input.
"""

from __future__ import annotations

from typing import Any
from core.llm.base import LLMProvider
from core.llm.models import LLMRequest, LLMResponse


class FakeLLMProvider(LLMProvider):
    """A fake provider that returns predictable responses."""

    def __init__(self, model: str = "fake-llm-v1"):
        self._model = model

    @property
    def supports_tools(self) -> bool:
        return True

    async def complete(
        self,
        request: LLMRequest,
        **kwargs: Any,
    ) -> LLMResponse:
        """Return a deterministic response."""

        # Simple deterministic logic: return a greeting if "Hello" is in the last message
        last_message = request.messages[-1].get("content", "") if request.messages else ""

        if "Hello" in last_message:
            content = "Hello! I am the Jarvis Fake LLM. How can I help you today?"
        else:
            content = "Fake LLM response to: " + (last_message or "empty request")

        return LLMResponse(
            content=content,
            model=self._model,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )

    async def health_check(self) -> bool:
        return True
