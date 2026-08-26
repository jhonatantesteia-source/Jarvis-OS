from core.llm.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)


def test_all_provider_errors_inherit_from_base():
    error_types = (
        LLMTimeoutError,
        LLMAuthenticationError,
        LLMRateLimitError,
        LLMConnectionError,
    )

    for error_type in error_types:
        assert issubclass(error_type, LLMProviderError)


def test_all_provider_errors_can_be_instantiated():
    error_types = (
        LLMProviderError,
        LLMTimeoutError,
        LLMAuthenticationError,
        LLMRateLimitError,
        LLMConnectionError,
    )

    for error_type in error_types:
        error = error_type("test error")
        assert str(error) == "test error"