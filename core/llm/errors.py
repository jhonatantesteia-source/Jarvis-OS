"""Exceptions raised by LLM providers."""

from __future__ import annotations


class LLMProviderError(Exception):
    """Base exception for provider-level LLM failures."""


class LLMTimeoutError(LLMProviderError):
    """Raised when an LLM provider request times out."""


class LLMAuthenticationError(LLMProviderError):
    """Raised when LLM provider authentication fails."""


class LLMRateLimitError(LLMProviderError):
    """Raised when an LLM provider rate limit is exceeded."""


class LLMConnectionError(LLMProviderError):
    """Raised when connection to an LLM provider fails."""