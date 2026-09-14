import pytest
import asyncio
import time
from typing import Any, Mapping

from core.tools import Tool, ToolRegistry, ToolResult
from core.agent.models import ToolCall
from core.tools.boundary import ValidatedToolCall
from core.tools.policy import PolicyDecision, PolicyDecisionType, ToolRiskLevel
from core.tools.executor import ToolExecutor
from core.approval.base import ApprovalGrant
from core.approval.errors import (
    AuthorizationError,
    ApprovalReplayError,
    ApprovalExpiredError,
)

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
    call = ToolCall(
        name=tool.name,
        arguments={},
        id="provider_id",
        internal_id="internal_id"
    )
    return ValidatedToolCall(
        tool=tool,
        call=call,
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
        request_id="internal_id",
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

@pytest.mark.anyio
async def test_wrong_tool_binding(executor, valid_call, valid_grant):
    call, tool = valid_call
    wrong_grant = ApprovalGrant(
        grant_id="grant_wrong_tool",
        request_id=call.call.internal_id,
        tool_name="wrong_tool",
        arguments=call.call.arguments,
        expires_at=time.time() + 300
    )
    with pytest.raises(AuthorizationError, match="bound to a different tool"):
        await executor.execute(call, grant=wrong_grant)
    assert tool.call_count == 0

@pytest.mark.anyio
async def test_wrong_arguments_binding(executor, valid_call, valid_grant):
    call, tool = valid_call
    wrong_grant = ApprovalGrant(
        grant_id="grant_wrong_args",
        request_id=call.call.internal_id,
        tool_name=call.tool.name,
        arguments={"wrong": "args"},
        expires_at=time.time() + 300
    )
    with pytest.raises(AuthorizationError, match="arguments do not match the call"):
        await executor.execute(call, grant=wrong_grant)
    assert tool.call_count == 0

@pytest.mark.anyio
async def test_wrong_request_id_binding(executor, valid_call, valid_grant):
    call, tool = valid_call
    wrong_grant = ApprovalGrant(
        grant_id="grant_wrong_id",
        request_id="wrong_internal_id",
        tool_name=call.tool.name,
        arguments=call.call.arguments,
        expires_at=time.time() + 300
    )
    with pytest.raises(AuthorizationError, match="bound to a different request"):
        await executor.execute(call, grant=wrong_grant)
    assert tool.call_count == 0

@pytest.mark.anyio
async def test_expired_grant(executor, valid_call, valid_grant):
    call, tool = valid_call
    expired_grant = ApprovalGrant(
        grant_id="grant_expired",
        request_id=call.call.internal_id,
        tool_name=call.tool.name,
        arguments=call.call.arguments,
        expires_at=time.time() - 10
    )
    with pytest.raises(ApprovalExpiredError, match="grant has expired"):
        await executor.execute(call, grant=expired_grant)
    assert tool.call_count == 0

@pytest.mark.anyio
async def test_exact_expiration_boundary(executor, valid_call, valid_grant):
    call, tool = valid_call
    now = time.time()
    exact_grant = ApprovalGrant(
        grant_id="grant_exact",
        request_id=call.call.internal_id,
        tool_name=call.tool.name,
        arguments=call.call.arguments,
        expires_at=now
    )
    with pytest.raises(ApprovalExpiredError, match="grant has expired"):
        await executor.execute(call, grant=exact_grant)
    assert tool.call_count == 0
