"""Factory for creating configured LLM providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.llm.base import LLMProvider

if TYPE_CHECKING:
    from core.config.settings import Settings


class UnsupportedLLMProviderError(ValueError):
    """Raised when an unsupported LLM provider is requested."""


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Create the configured LLM provider.

    Concrete providers are intentionally not implemented yet.
    """
    provider_name = settings.llm_provider.strip().lower()

    if not provider_name:
        raise UnsupportedLLMProviderError(
            "LLM provider cannot be empty."
        )

    raise UnsupportedLLMProviderError(
        f"LLM provider '{provider_name}' is not implemented."
    )