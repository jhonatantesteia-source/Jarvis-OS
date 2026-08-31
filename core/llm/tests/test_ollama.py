import pytest
import pytest_asyncio
from core.llm.providers.ollama import OllamaProvider
from core.llm.models import LLMRequest, LLMResponse
from core.config.settings import settings

@pytest.mark.ollama
class TestOllamaProvider:
    @pytest_asyncio.fixture
    async def provider(self):
        provider = OllamaProvider(model="qwen3:1.7b")
        yield provider
        await provider._client.aclose()

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        """Verify Ollama is reachable."""
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_completion(self, provider):
        """Verify simple text completion."""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello!"}],
            temperature=0.7,
            max_tokens=128
        )
        response = await provider.complete(request)
        assert isinstance(response, LLMResponse)
        assert response.content != ""

    @pytest.mark.asyncio
    async def test_tool_calling_generation(self, provider):
        """Verify Ollama generates structured tool calls."""
        request = LLMRequest(
            messages=[{"role": "user", "content": "What time is it?"}],
            max_tokens=512,
        )
        tools = [

            {
                "name": "get_current_time",
                "description": "Get the current system time",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]

        response = await provider.complete(request, tools=tools)

        assert len(response.tool_calls) > 0
        tool_call = response.tool_calls[0]
        assert tool_call["name"] == "get_current_time"
        assert isinstance(tool_call["arguments"], dict)
