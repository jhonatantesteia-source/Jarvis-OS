import pytest
import asyncio
import time
from typing import Any, Mapping

from core.tools import Tool, ToolRegistry, ToolResult
from core.tools.boundary import ValidatedToolCall
from core.tools.policy import PolicyDecision, PolicyDecisionType, ToolRiskLevel
from core.tools.executor import ToolExecutor
from core.approval.base import ApprovalGrant
from core.approval.errors import ApprovalReplayError

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

@pytest.fixture
def executor():
    return ToolExecutor()

@pytest.fixture
def valid_call():
    tool = MockTool()
    # ToolCall for the inner call
    class MockCall:
        id = "call_1"
        arguments = {}

    # ValidatedToolCall wraps a call and a tool
    return ValidatedToolCall(
        tool=tool,
        call=MockCall(),
        decision=PolicyDecision(
            decision=PolicyDecisionType.REQUIRE_USER_APPROVAL,
            risk_level=ToolRiskLevel.HIGH,
            reason="Test"
        )
    ), tool

@pytest.fixture
def valid_grant():
    return ApprovalGrant(
        grant_id="grant_1",
        request_id="call_1",
        tool_name="test_tool",
        arguments={},
        expires_at=time.time() + 300
    )

@pytest.mark.anyio
async def test_exactly_once_execution(executor, valid_call, valid_grant):
    call, tool = valid_call

    # Execute once
    result = await executor.execute(call, grant=valid_grant)
    assert result.success is True
    assert tool.call_count == 1

    # Try to execute again with same grant
    with pytest.raises(ApprovalReplayError):
        await executor.execute(call, grant=valid_grant)

    assert tool.call_count == 1

@pytest.mark.anyio
async def test_concurrent_replay_protection(executor, valid_call, valid_grant):
    call, tool = valid_call

    # Attempt two concurrent executions with the same grant
    # We use asyncio.gather to launch them concurrently
    results = await asyncio.gather(
        executor.execute(call, grant=valid_grant),
        executor.execute(call, grant=valid_grant),
        return_exceptions=True
    )

    # One should succeed, one should be an ApprovalReplayError
    successes = [r for r in results if isinstance(r, ToolResult) and r.success]
    replays = [r for r in results if isinstance(r, ApprovalReplayError)]

    assert len(successes) == 1
    assert len(replays) == 1
    assert tool.call_count == 1
