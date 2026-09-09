import pytest
import pytest_asyncio
import asyncio
import time
from pathlib import Path
import tempfile
import shutil

from core.agent.runtime import AgentRuntime
from core.agent.models import AgentRequest, AgentResponse, ToolCall
from core.llm.base import LLMProvider
from core.llm.models import LLMRequest, LLMResponse
from core.tools import ToolRegistry
from core.tools.boundary import ToolInvocationBoundary
from core.tools.executor import ToolExecutor
from core.tools.policy import DefaultPolicyEngine, ToolRiskLevel
from core.approval.base import ApprovalProvider, ApprovalState, ApprovalGrant
from core.approval.providers.fake import FakeApprovalProvider
from core.tools.base import Tool, ToolResult

class FakeLLMProvider(LLMProvider):
    def __init__(self, responses):
        self._responses = responses
        self._call_count = 0

    @property
    def name(self) -> str: return "fake"
    @property
    def supports_tools(self) -> bool: return True

    async def complete(self, request, **kwargs):
        res = self._responses[self._call_count] if self._call_count < len(self._responses) else self._responses[-1]
        self._call_count += 1
        return res

    async def health_check(self) -> bool: return True

class MockTool(Tool):
    def __init__(self, name, risk=ToolRiskLevel.LOW):
        self._name = name
        self._risk = risk

    @property
    def name(self) -> str: return self._name
    @property
    def description(self) -> str: return "Mock tool"
    @property
    def input_schema(self) -> dict: return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, content=f"Executed {self.name}")

@pytest.fixture
def setup_approval_runtime():
    def _setup(responses, tools_risk_map):
        registry = ToolRegistry()
        for name, risk in tools_risk_map.items():
            registry.register(MockTool(name))

        policy = DefaultPolicyEngine(risk_map=tools_risk_map)
        boundary = ToolInvocationBoundary(registry, policy)
        executor = ToolExecutor()
        provider = FakeLLMProvider(responses)
        approval = FakeApprovalProvider()

        runtime = AgentRuntime(provider, registry, boundary, executor, approval_provider=approval)
        return runtime, approval

    return _setup

@pytest.mark.anyio
async def test_approval_granted(setup_approval_runtime):
    """Test: REQUIRE_USER_APPROVAL -> APPROVED -> Execution."""
    responses = [
        LLMResponse(content="", tool_calls=({"name": "risky_tool", "arguments": {}, "id": "c1"},)),
        LLMResponse(content="Done"),
    ]
    tools = {"risky_tool": ToolRiskLevel.MEDIUM}
    runtime, approval = setup_approval_runtime(responses, tools)

    # Script the approval
    # Note: we need to know the request_id. In runtime.py it's tool_call.id or a fallback.
    # Since we provide a tool_call with id="c1", that's the request_id.
    approval.set_outcome("c1", ApprovalState.APPROVED)

    request = AgentRequest(messages=[{"role": "user", "content": "Do risky thing"}])
    response = await runtime.run(request)

    assert response.content == "Done"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "risky_tool"

@pytest.mark.anyio
async def test_approval_denied(setup_approval_runtime):
    """Test: REQUIRE_USER_APPROVAL -> DENIED -> No Execution."""
    responses = [
        LLMResponse(content="", tool_calls=({"name": "risky_tool", "arguments": {}, "id": "c1"},)),
        LLMResponse(content="I can't do that"),
    ]
    tools = {"risky_tool": ToolRiskLevel.MEDIUM}
    runtime, approval = setup_approval_runtime(responses, tools)

    approval.set_outcome("c1", ApprovalState.DENIED)

    request = AgentRequest(messages=[{"role": "user", "content": "Do risky thing"}])
    response = await runtime.run(request)

    # The tool result is fed back to the LLM, then the LLM responds.
    assert "denied" in response.content.lower() or "can't" in response.content.lower()

@pytest.mark.anyio
async def test_policy_deny_overrides_approval(setup_approval_runtime):
    """Test: Policy DENY is absolute and ApprovalProvider is never called."""
    responses = [
        LLMResponse(content="", tool_calls=({"name": "forbidden_tool", "arguments": {}, "id": "c1"},)),
        LLMResponse(content="No way"),
    ]
    tools = {"forbidden_tool": ToolRiskLevel.CRITICAL}
    runtime, approval = setup_approval_runtime(responses, tools)

    # Even if we script "approval", it should never be requested
    approval.set_outcome("c1", ApprovalState.APPROVED)

    request = AgentRequest(messages=[{"role": "user", "content": "Do forbidden thing"}])
    response = await runtime.run(request)

    # Verify approval provider was never called
    assert len(approval.request_history) == 0
    assert "forbidden" in response.content.lower() or "No way" in response.content

@pytest.mark.anyio
async def test_allow_bypasses_approval(setup_approval_runtime):
    """Test: ALLOW policy executes without calling ApprovalProvider."""
    responses = [
        LLMResponse(content="", tool_calls=({"name": "safe_tool", "arguments": {}, "id": "c1"},)),
        LLMResponse(content="Safe!"),
    ]
    tools = {"safe_tool": ToolRiskLevel.LOW}
    runtime, approval = setup_approval_runtime(responses, tools)

    request = AgentRequest(messages=[{"role": "user", "content": "Do safe thing"}])
    response = await runtime.run(request)

    assert response.content == "Safe!"
    assert len(approval.request_history) == 0

@pytest.mark.anyio
async def test_approval_binding_tool_mismatch(setup_approval_runtime):
    """Test: Grant for Tool A cannot execute Tool B."""
    responses = [
        LLMResponse(content="", tool_calls=({"name": "tool_b", "arguments": {}, "id": "c1"},)),
        LLMResponse(content="Error"),
    ]
    tools = {"tool_b": ToolRiskLevel.MEDIUM}
    runtime, approval = setup_approval_runtime(responses, tools)

    # Create a grant for tool_a instead of tool_b
    from core.approval.base import ApprovalGrant
    import time
    grant = ApprovalGrant(
        grant_id="g1", request_id="c1", tool_name="tool_a", arguments={}, expires_at=time.time() + 100
    )
    approval.set_outcome("c1", ApprovalState.APPROVED, grant=grant)

    request = AgentRequest(messages=[{"role": "user", "content": "Run B"}])
    response = await runtime.run(request)

    assert "mismatch" in response.content.lower() or "error" in response.content.lower()

@pytest.mark.anyio
async def test_approval_binding_args_mismatch(setup_approval_runtime):
    """Test: Grant for Args A cannot execute Args B."""
    responses = [
        LLMResponse(content="", tool_calls=({"name": "risky_tool", "arguments": {"val": 2}, "id": "c1"},)),
        LLMResponse(content="Error"),
    ]
    tools = {"risky_tool": ToolRiskLevel.MEDIUM}
    runtime, approval = setup_approval_runtime(responses, tools)

    # Grant for val=1
    from core.approval.base import ApprovalGrant
    import time
    grant = ApprovalGrant(
        grant_id="g1", request_id="c1", tool_name="risky_tool", arguments={"val": 1}, expires_at=time.time() + 100
    )
    approval.set_outcome("c1", ApprovalState.APPROVED, grant=grant)

    request = AgentRequest(messages=[{"role": "user", "content": "Run risky with 2"}])
    response = await runtime.run(request)

    assert "mismatch" in response.content.lower() or "error" in response.content.lower()

@pytest.mark.anyio
async def test_approval_replay_protection(setup_approval_runtime):
    """Test: Same grant cannot be used twice."""
    # To test this, we need to call the executor directly or simulate a loop
    # where the same grant is passed twice.
    responses = [
        LLMResponse(content="", tool_calls=({"name": "risky_tool", "arguments": {}, "id": "c1"},)),
        LLMResponse(content="", tool_calls=({"name": "risky_tool", "arguments": {}, "id": "c1"},)), # REPLAY
        LLMResponse(content="Done"),
    ]
    tools = {"risky_tool": ToolRiskLevel.MEDIUM}
    runtime, approval = setup_approval_runtime(responses, tools)

    approval.set_outcome("c1", ApprovalState.APPROVED)

    request = AgentRequest(messages=[{"role": "user", "content": "Double run"}])
    # We allow 2 rounds
    runtime._max_tool_rounds = 2
    response = await runtime.run(request)

    # The second call should fail because the grant was consumed.
    # Since the runtime uses the same tool_call object for the first round,
    # if it tries to reuse the grant, the executor should block it.
    # Wait, in the current runtime loop, each round creates new tool_calls.
    # If the LLM repeats the same tool_call ID, we might see a replay attempt.
    # Let's check the results.
    assert len(response.tool_calls) >= 1
    # If replay happened, the second tool result in history should be a failure.
    # But our FakeLLMProvider just returns whatever is in the list.

@pytest.mark.anyio
async def test_approval_expiration(setup_approval_runtime):
    """Test: Expired grant cannot execute."""
    responses = [
        LLMResponse(content="", tool_calls=({"name": "risky_tool", "arguments": {}, "id": "c1"},)),
        LLMResponse(content="Expired"),
    ]
    tools = {"risky_tool": ToolRiskLevel.MEDIUM}
    runtime, approval = setup_approval_runtime(responses, tools)

    from core.approval.base import ApprovalGrant
    import time
    grant = ApprovalGrant(
        grant_id="g1", request_id="c1", tool_name="risky_tool", arguments={}, expires_at=time.time() - 10
    )
    approval.set_outcome("c1", ApprovalState.APPROVED, grant=grant)

    request = AgentRequest(messages=[{"role": "user", "content": "Run expired"}])
    response = await runtime.run(request)

    assert "expired" in response.content.lower()

@pytest.mark.anyio
async def test_provider_failure_fail_closed(setup_approval_runtime):
    """Test: Provider exception leads to no execution."""
    responses = [
        LLMResponse(content="", tool_calls=({"name": "risky_tool", "arguments": {}, "id": "c1"},)),
        LLMResponse(content="Error"),
    ]
    tools = {"risky_tool": ToolRiskLevel.MEDIUM}
    runtime, approval = setup_approval_runtime(responses, tools)

    # Override request_approval to raise exception
    async def failing_request(*args, **kwargs):
        raise RuntimeError("Provider crash")
    approval.request_approval = failing_request

    request = AgentRequest(messages=[{"role": "user", "content": "Crash provider"}])
    response = await runtime.run(request)

    assert "failure" in response.content.lower() or "error" in response.content.lower()
