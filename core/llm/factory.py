"""Factory for creating configured LLM providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.llm.base import LLMProvider
from core.llm.providers.fake import FakeLLMProvider
from core.llm.providers.ollama import OllamaProvider

if TYPE_CHECKING:
    from core.config.settings import Settings


class UnsupportedLLMProviderError(ValueError):
    """Raised when an unsupported LLM provider is requested."""


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Create the configured LLM provider.

    Supported providers:
    - fake: Deterministic provider for testing.
    - ollama: Local LLM runtime provider.
    """
    provider_name = settings.llm_provider.strip().lower()

    if not provider_name:
        raise UnsupportedLLMProviderError(
            "LLM provider cannot be empty."
        )

    if provider_name == "fake":
        return FakeLLMProvider(model=settings.llm_model or "fake-llm-v1")

    if provider_name == "ollama":
        return OllamaProvider(model=settings.llm_model)

    raise UnsupportedLLMProviderError(
        f"LLM provider '{provider_name}' is not implemented."
    )