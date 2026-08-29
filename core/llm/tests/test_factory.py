import pytest

from core.config.settings import Settings
from core.llm.factory import (
    UnsupportedLLMProviderError,
    create_llm_provider,
)


def test_factory_rejects_empty_provider():
    settings = Settings(llm_provider="")

    with pytest.raises(
        UnsupportedLLMProviderError,
        match="LLM provider cannot be empty",
    ):
        create_llm_provider(settings)


def test_factory_rejects_unimplemented_provider():
    settings = Settings(llm_provider="openai")

    with pytest.raises(
        UnsupportedLLMProviderError,
        match="LLM provider 'openai' is not implemented",
    ):
        create_llm_provider(settings)


def test_factory_normalizes_provider_name():
    settings = Settings(llm_provider="  OPENAI  ")

    with pytest.raises(
        UnsupportedLLMProviderError,
        match="LLM provider 'openai' is not implemented",
    ):
        create_llm_provider(settings)


def test_settings_loads_llm_configuration():
    settings = Settings(
        llm_provider="anthropic",
        llm_model="test-model",
    )

    assert settings.llm_provider == "anthropic"
    assert settings.llm_model == "test-model"


def test_factory_creates_fake_provider():
    settings = Settings(llm_provider="fake")
    provider = create_llm_provider(settings)
    assert provider.__class__.__name__ == "FakeLLMProvider"

