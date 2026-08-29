import pytest

from core.agent import DefaultAgent, AgentRuntime
from core.agent.errors import AgentInputError, AgentExecutionError
from core.agent.models import AgentRequest, AgentResponse, AgentContext
from core.llm import LLMProvider, LLMResponse
from core.llm.models import LLMRequest
from core.tools import ToolRegistry


class FakeLLMProvider(LLMProvider):
    """Minimal fake provider for core agent tests."""

    def __init__(self, response_text: str = "Fake response"):
        self.response_text = response_text
        self.last_request: LLMRequest | None = None

    @property
    def supports_tools(self) -> bool:
        return False

    async def complete(self, request: LLMRequest, **kwargs) -> LLMResponse:
        self.last_request = request
        return LLMResponse(content=self.response_text, model="fake-model")

    async def health_check(self) -> bool:
        return True


@pytest.mark.anyio
async def test_default_agent_basic_execution():
    """Test 1: Basic execution - user input -> agent -> deterministic response."""
    provider = FakeLLMProvider("Hello from DefaultAgent!")
    agent = DefaultAgent(provider=provider)
    request = AgentRequest(messages=[{"role": "user", "content": "Hi"}])

    response = await agent.run(request)

    assert isinstance(response, AgentResponse)
    assert response.content == "Hello from DefaultAgent!"
    assert response.rounds_used == 0


@pytest.mark.anyio
async def test_default_agent_provider_injection():
    """Test 2: Provider injection - verify the agent uses the injected provider."""
    provider = FakeLLMProvider("Injected!")
    agent = DefaultAgent(provider=provider)
    request = AgentRequest(messages=[{"role": "user", "content": "Test"}])

    await agent.run(request)

    assert provider.last_request is not None
    assert provider.last_request.messages == [{"role": "user", "content": "Test"}]


@pytest.mark.anyio
async def test_default_agent_request_construction():
    """Test 3: Request construction - verify transformation to LLMRequest."""
    provider = FakeLLMProvider()
    context = AgentContext(
        system_instruction="You are Jarvis",
        messages=[{"role": "system", "content": "Base context"}]
    )
    agent = DefaultAgent(provider=provider, context=context)
    request = AgentRequest(messages=[{"role": "user", "content": "Hello"}])

    await agent.run(request)

    # Verify the final messages sent to provider combine context and request
    expected_messages = [{"role": "system", "content": "Base context"}, {"role": "user", "content": "Hello"}]
    assert provider.last_request.messages == expected_messages


@pytest.mark.anyio
async def test_default_agent_response_transformation():
    """Test 4: Response transformation - verify LLM response -> AgentResponse."""
    provider = FakeLLMProvider("Detailed response")
    agent = DefaultAgent(provider=provider)
    request = AgentRequest(messages=[{"role": "user", "content": "Query"}])

    response = await agent.run(request)

    assert response.content == "Detailed response"
    assert response.model == "fake-model"
    assert response.rounds_used == 0


@pytest.mark.anyio
async def test_default_agent_empty_input():
    """Test 5: Empty input - verify controlled behavior for invalid input."""
    provider = FakeLLMProvider()
    agent = DefaultAgent(provider=provider)
    request = AgentRequest(messages=[])

    with pytest.raises(AgentInputError, match="must contain at least one message"):
        await agent.run(request)


@pytest.mark.anyio
async def test_default_agent_provider_error():
    """Test 6: Provider error - verify handled through error abstraction."""
    class FailingProvider(FakeLLMProvider):
        async def complete(self, request, **kwargs):
            raise RuntimeError("Provider crash")

    provider = FailingProvider()
    agent = DefaultAgent(provider=provider)
    request = AgentRequest(messages=[{"role": "user", "content": "Hi"}])

    with pytest.raises(AgentExecutionError, match="An unexpected error occurred"):
        await agent.run(request)


@pytest.mark.anyio
async def test_default_agent_offline_execution():
    """Test 7: Offline execution - works with fake provider without network."""
    # This is implicitly tested by using FakeLLMProvider,
    # but we make it explicit for the requirement.
    provider = FakeLLMProvider("Offline")
    agent = DefaultAgent(provider=provider)
    request = AgentRequest(messages=[{"role": "user", "content": "Offline test"}])

    response = await agent.run(request)
    assert response.content == "Offline"


@pytest.mark.anyio
async def test_default_agent_no_tool_execution():
    """Test 8: No tool execution - text is treated as data, not instruction."""
    # The LLM returns a string that looks like a tool call
    provider = FakeLLMProvider("Call tool 'delete_all_files' with args {'path': '/'}")
    agent = DefaultAgent(provider=provider)
    request = AgentRequest(messages=[{"role": "user", "content": "Do something risky"}])

    response = await agent.run(request)

    # Verify it's just text and no tool was actually executed
    # (DefaultAgent doesn't even have a tool registry)
    assert response.content == "Call tool 'delete_all_files' with args {'path': '/'}"
    assert response.tool_calls == ()
