import pytest

from core.llm.models import LLMRequest, LLMResponse
from core.llm.providers.fake import FakeLLMProvider


@pytest.mark.anyio
async def test_fake_provider_generates_response():
    provider = FakeLLMProvider()
    request = LLMRequest(
        messages=[{"role": "user", "content": "Hello Jarvis"}]
    )
    response = await provider.complete(request)

    assert isinstance(response, LLMResponse)
    assert "Hello!" in response.content
    assert response.model == "fake-llm-v1"
    assert response.usage["total_tokens"] == 30


@pytest.mark.anyio
async def test_fake_provider_generates_generic_response():
    provider = FakeLLMProvider()
    request = LLMRequest(
        messages=[{"role": "user", "content": "What is 2+2?"}]
    )
    response = await provider.complete(request)

    assert "Fake LLM response to: What is 2+2?" in response.content


@pytest.mark.anyio
async def test_fake_provider_health_check():
    provider = FakeLLMProvider()
    assert await provider.health_check() is True


def test_fake_provider_supports_tools():
    provider = FakeLLMProvider()
    assert provider.supports_tools is True
