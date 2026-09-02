import pytest
import pytest_asyncio
from typing import Any, Mapping, Sequence
from core.agent.runtime import AgentRuntime
from core.agent.models import AgentRequest, AgentResponse, ToolCall, AgentContext
from core.llm.base import LLMProvider
from core.llm.models import LLMRequest, LLMResponse
from core.tools.base import Tool, ToolResult
from core.tools.registry import ToolRegistry
from core.tools.boundary import ToolInvocationBoundary, PolicyDeniedError
from core.tools.policy import DefaultPolicyEngine, ToolRiskLevel
from core.tools.executor import ToolExecutor
from core.agent.errors import AgentExecutionError

class FakeLLMProvider(LLMProvider):
    """A deterministic LLM provider for testing loops."""
    def __init__(self, responses: Sequence[LLMResponse]):
        self._responses = responses
        self._call_count = 0

    @property
    def supports_tools(self) -> bool:
        return True

    async def complete(self, request: LLMRequest, **kwargs: Any) -> LLMResponse:
        if self._call_count >= len(self._responses):
            # Default to the last response or a simple one
            return self._responses[-1] if self._responses else LLMResponse(content="Error: No responses configured")

        res = self._responses[self._call_count]
        self._call_count += 1
        return res

    async def health_check(self) -> bool:
        return True

class MockTool(Tool):
    """A simple tool for testing."""
    def __init__(self, name: str, result_content: str = "Mock result", should_fail: bool = False):
        self._name = name
        self._result_content = result_content
        self._should_fail = should_fail

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Mock tool"

    @property
    def input_schema(self) -> Mapping[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> ToolResult:
        if self._should_fail:
            raise Exception("Tool crashed!")
        return ToolResult(success=True, content=self._result_content)

@pytest.fixture
def setup_loop():
    def _setup(responses, tools_data):
        registry = ToolRegistry()
        risk_map = {}
        for name, data in tools_data.items():
            tool = MockTool(name, result_content=data.get("result", "Mock result"), should_fail=data.get("fail", False))
            registry.register(tool)
            risk_map[name] = data.get("risk", ToolRiskLevel.LOW)

        policy = DefaultPolicyEngine(risk_map=risk_map)
        boundary = ToolInvocationBoundary(registry, policy)
        executor = ToolExecutor()
        provider = FakeLLMProvider(responses)

        runtime = AgentRuntime(provider, registry, boundary, executor)
        return runtime

    return _setup

@pytest.mark.anyio
async def test_loop_direct_response(setup_loop):
    """LLM returns text immediately -> 0 rounds."""
    responses = [LLMResponse(content="Hello!")]
    runtime = setup_loop(responses, {})

    request = AgentRequest(messages=[{"role": "user", "content": "Hi"}])
    response = await runtime.run(request)

    assert response.content == "Hello!"
    assert response.rounds_used == 0
    assert len(response.tool_calls) == 0

@pytest.mark.anyio
async def test_loop_single_round(setup_loop):
    """LLM -> Tool Call -> Result -> LLM -> Final Answer -> 1 round."""
    responses = [
        LLMResponse(content="", tool_calls=[{"name": "get_time", "arguments": {}, "id": "call_1"}]),
        LLMResponse(content="The time is 12:00")
    ]
    tools = {"get_time": {"result": "12:00"}}
    runtime = setup_loop(responses, tools)

    request = AgentRequest(messages=[{"role": "user", "content": "What time is it?"}])
    response = await runtime.run(request)

    assert response.content == "The time is 12:00"
    assert response.rounds_used == 1
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "get_time"

@pytest.mark.anyio
async def test_loop_multiple_rounds(setup_loop):
    """LLM -> Tool A -> Result A -> LLM -> Tool B -> Result B -> LLM -> Final Answer -> 2 rounds."""
    responses = [
        LLMResponse(content="", tool_calls=[{"name": "tool_a", "arguments": {}, "id": "call_1"}]),
        LLMResponse(content="", tool_calls=[{"name": "tool_b", "arguments": {}, "id": "call_2"}]),
        LLMResponse(content="Final result")
    ]
    tools = {"tool_a": {"result": "A"}, "tool_b": {"result": "B"}}
    runtime = setup_loop(responses, tools)

    request = AgentRequest(messages=[{"role": "user", "content": "Run a and b"}])
    response = await runtime.run(request)

    assert response.content == "Final result"
    assert response.rounds_used == 2
    assert len(response.tool_calls) == 2

@pytest.mark.anyio
async def test_loop_denied_tool(setup_loop):
    """LLM -> Denied Tool -> Error Result -> LLM -> Final Answer."""
    responses = [
        LLMResponse(content="", tool_calls=[{"name": "secret_tool", "arguments": {}, "id": "call_1"}]),
        LLMResponse(content="Sorry, I couldn't access that tool.")
    ]
    # Critical risk tools are denied by default policy
    tools = {"secret_tool": {"risk": ToolRiskLevel.CRITICAL}}
    runtime = setup_loop(responses, tools)

    request = AgentRequest(messages=[{"role": "user", "content": "Use secret tool"}])
    response = await runtime.run(request)

    assert "Sorry" in response.content
    assert response.rounds_used == 1
    assert len(response.tool_calls) == 1

@pytest.mark.anyio
async def test_loop_approval_required(setup_loop):
    """LLM -> Approval-needed Tool -> Error Result -> LLM -> Final Answer."""
    responses = [
        LLMResponse(content="", tool_calls=[{"name": "med_tool", "arguments": {}, "id": "call_1"}]),
        LLMResponse(content="I need approval for that tool.")
    ]
    # Medium risk tools require approval
    tools = {"med_tool": {"risk": ToolRiskLevel.MEDIUM}}
    runtime = setup_loop(responses, tools)

    request = AgentRequest(messages=[{"role": "user", "content": "Use med tool"}])
    response = await runtime.run(request)

    assert "approval" in response.content.lower()
    assert response.rounds_used == 1

@pytest.mark.anyio
async def test_loop_tool_failure(setup_loop):
    """LLM -> Tool (crashes) -> Error Result -> LLM -> Final Answer."""
    responses = [
        LLMResponse(content="", tool_calls=[{"name": "broken_tool", "arguments": {}, "id": "call_1"}]),
        LLMResponse(content="The tool failed, but here is my best guess.")
    ]
    tools = {"broken_tool": {"fail": True}}
    runtime = setup_loop(responses, tools)

    request = AgentRequest(messages=[{"role": "user", "content": "Use broken tool"}])
    response = await runtime.run(request)

    assert "best guess" in response.content
    assert response.rounds_used == 1

@pytest.mark.anyio
async def test_loop_max_iterations(setup_loop):
    """LLM -> Tool -> Result -> LLM -> Tool... (up to limit) -> Stop."""
    # Provider always returns a tool call
    responses = [
        LLMResponse(content="", tool_calls=[{"name": "loop_tool", "arguments": {}, "id": f"call_{i}"}])
        for i in range(10)
    ]
    tools = {"loop_tool": {"result": "looping"}}
    runtime = setup_loop(responses, tools)
    runtime._max_tool_rounds = 3

    request = AgentRequest(messages=[{"role": "user", "content": "Loop forever"}])
    response = await runtime.run(request)

    assert "Max tool rounds (3) reached" in response.content
    assert response.rounds_used == 3
    assert len(response.tool_calls) == 3

@pytest.mark.anyio
async def test_loop_provider_failure(setup_loop):
    """LLMProvider raises exception -> AgentExecutionError."""
    class FailingProvider(LLMProvider):
        @property
        def supports_tools(self) -> bool: return True
        async def complete(self, request, **kwargs): raise RuntimeError("API Down")
        async def health_check(self) -> bool: return False

    registry = ToolRegistry()
    boundary = ToolInvocationBoundary(registry, DefaultPolicyEngine())
    executor = ToolExecutor()
    runtime = AgentRuntime(FailingProvider(), registry, boundary, executor)

    request = AgentRequest(messages=[{"role": "user", "content": "Hi"}])
    with pytest.raises(AgentExecutionError):
        await runtime.run(request)
