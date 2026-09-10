import pytest
import asyncio
import time
from typing import Any, Mapping, Sequence

from core.agent import AgentRequest, AgentRuntime
from core.llm import LLMProvider
from core.llm.models import LLMRequest, LLMResponse
from core.tools import Tool, ToolRegistry, ToolResult
from core.tools.boundary import ToolInvocationBoundary
from core.tools.policy import DefaultPolicyEngine, ToolRiskLevel, PolicyDecisionType
from core.tools.executor import ToolExecutor
from core.approval.base import (
    ApprovalProvider,
    ApprovalRequest,
    ApprovalResult,
    ApprovalState,
    ApprovalGrant
)

class FakeLLMProvider(LLMProvider):
    def __init__(self, responses: Sequence[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[LLMRequest] = []
    @property
    def name(self) -> str: return "fake"
    @property
    def supports_tools(self) -> bool: return True
    async def complete(self, request: LLMRequest, **kwargs: Any) -> LLMResponse:
        self.calls.append(request)
        return self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]
    async def health_check(self) -> bool: return True

class MockTool(Tool):
    def __init__(self, name="test_tool"):
        self._name = name
        self.call_count = 0
    @property
    def name(self) -> str: return self._name
    @property
    def description(self) -> str: return "Test tool"
    @property
    def input_schema(self) -> Mapping[str, Any]: return {"type": "object", "properties": {}}
    async def execute(self, **kwargs: Any) -> ToolResult:
        self.call_count += 1
        return ToolResult(success=True, content="executed")

class MismatchedApprovalProvider(ApprovalProvider):
    @property
    def name(self) -> str: return "mismatched"
    async def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
        return ApprovalResult(
            request_id="wrong_id",
            state=ApprovalState.APPROVED,
            grant=ApprovalGrant(
                grant_id="g1",
                request_id="wrong_id",
                tool_name=request.tool_name,
                arguments=request.arguments,
                expires_at=time.time() + 300
            )
        )

class BlockingApprovalProvider(ApprovalProvider):
    def __init__(self):
        self.event = asyncio.Event()
    @property
    def name(self) -> str: return "blocking"
    async def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
        await self.event.wait()
        return ApprovalResult(
            request_id=request.request_id,
            state=ApprovalState.APPROVED,
            grant=ApprovalGrant(
                grant_id="g1",
                request_id=request.request_id,
                tool_name=request.tool_name,
                arguments=request.arguments,
                expires_at=time.time() + 300
            )
        )

def runtime_setup(provider, approval_provider=None, tools=None):
    registry = ToolRegistry()
    if tools:
        for tool in tools:
            registry.register(tool)
    boundary = ToolInvocationBoundary(registry, DefaultPolicyEngine())
    executor = ToolExecutor()
    return AgentRuntime(provider, registry, boundary, executor, approval_provider=approval_provider)

@pytest.mark.anyio
async def test_approval_result_request_id_mismatch():
    tool = MockTool()
    tool_call = {"id": "call_1", "name": tool.name, "arguments": {}}
    provider = FakeLLMProvider([
        LLMResponse(content="Checking...", tool_calls=(tool_call,)),
        LLMResponse(content="Done")
    ])
    approval_provider = MismatchedApprovalProvider()
    agent = runtime_setup(provider, approval_provider, [tool])

    class AlwaysRequireApprovalPolicy:
        def authorize(self, tool, call):
            from core.tools.policy import PolicyDecision
            return PolicyDecision(decision=PolicyDecisionType.REQUIRE_USER_APPROVAL, risk_level=ToolRiskLevel.HIGH, reason="Test")
    agent._boundary._policy_engine = AlwaysRequireApprovalPolicy()

    response = await agent.run(AgentRequest(messages=[{"role": "user", "content": "test"}]))

    # Verify that the tool result containing the mismatch error was sent back to the LLM
    assert len(provider.calls) >= 2
    history = provider.calls[1].messages
    tool_results = [m for m in history if m.get("role") == "tool"]

    if not any("Approval result identity mismatch" in str(m.get("content")) for m in tool_results):
        pytest.fail(f"Tool results did not contain expected error. Found: {tool_results}")

@pytest.mark.anyio
async def test_approval_cancellation_prevents_execution():
    tool = MockTool()
    tool_call = {"id": "call_1", "name": tool.name, "arguments": {}}
    provider = FakeLLMProvider([
        LLMResponse(content="Checking...", tool_calls=(tool_call,)),
        LLMResponse(content="Done")
    ])
    approval_provider = BlockingApprovalProvider()
    agent = runtime_setup(provider, approval_provider, [tool])

    class AlwaysRequireApprovalPolicy:
        def authorize(self, tool, call):
            from core.tools.policy import PolicyDecision
            return PolicyDecision(decision=PolicyDecisionType.REQUIRE_USER_APPROVAL, risk_level=ToolRiskLevel.HIGH, reason="Test")
    agent._boundary._policy_engine = AlwaysRequireApprovalPolicy()

    task = asyncio.create_task(agent.run(AgentRequest(messages=[{"role": "user", "content": "test"}])))
    await asyncio.sleep(0.1)
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    assert tool.call_count == 0
