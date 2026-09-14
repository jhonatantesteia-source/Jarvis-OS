import pytest
from unittest.mock import AsyncMock, MagicMock

from core.agent.models import ToolCall
from core.tools.base import Tool, ToolResult
from core.tools.boundary import (
    ValidatedToolCall,
    ApprovalRequiredError,
)
from core.tools.executor import ToolExecutor
from core.tools.policy import PolicyDecision, PolicyDecisionType, ToolRiskLevel


class MockTool(Tool):
    """A tool for testing the executor."""

    def __init__(self, name: str, schema: dict):
        self._name = name
        self._schema = schema

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Mock tool"

    @property
    def input_schema(self) -> dict:
        return self._schema

    async def execute(self, **kwargs):
        return ToolResult(success=True, content=f"Executed {self.name} with {kwargs}")


@pytest.mark.anyio
async def test_executor_authorized_allow():
    """Verify that a tool with ALLOW decision executes successfully."""
    tool = MockTool("allow_tool", {"type": "object", "properties": {}})
    call = ToolCall(name="allow_tool", arguments={"arg1": "val1"})
    decision = PolicyDecision(
        decision=PolicyDecisionType.ALLOW,
        reason="Allowed",
        risk_level=ToolRiskLevel.LOW
    )
    validated = ValidatedToolCall(tool=tool, call=call, decision=decision)

    executor = ToolExecutor()
    result = await executor.execute(validated)

    assert result.success is True
    assert "Executed allow_tool" in result.content


@pytest.mark.anyio
async def test_executor_authorized_approved():
    """Verify that a tool requiring approval executes if approved=True."""
    tool = MockTool("approval_tool", {"type": "object", "properties": {}})
    # Add internal_id for security boundary
    call = ToolCall(name="approval_tool", arguments={}, id="call_1", internal_id="internal_1")
    decision = PolicyDecision(
        decision=PolicyDecisionType.REQUIRE_USER_APPROVAL,
        reason="Approval needed",
        risk_level=ToolRiskLevel.MEDIUM
    )
    validated = ValidatedToolCall(tool=tool, call=call, decision=decision)

    executor = ToolExecutor()
    # Use a fake grant instead of approved=True
    from core.approval.base import ApprovalGrant
    import time
    grant = ApprovalGrant(
        grant_id="g1", request_id="internal_1", tool_name=tool.name,
        arguments=call.arguments, expires_at=time.time() + 100
    )
    result = await executor.execute(validated, grant=grant)

    assert result.success is True
    assert "Executed approval_tool" in result.content


@pytest.mark.anyio
async def test_executor_denies_unapproved():
    """Verify that a tool requiring approval raises ApprovalRequiredError if approved=False."""
    tool = MockTool("approval_tool", {"type": "object", "properties": {}})
    call = ToolCall(name="approval_tool", arguments={})
    decision = PolicyDecision(
        decision=PolicyDecisionType.REQUIRE_USER_APPROVAL,
        reason="Approval needed",
        risk_level=ToolRiskLevel.MEDIUM
    )
    validated = ValidatedToolCall(tool=tool, call=call, decision=decision)

    executor = ToolExecutor()
    with pytest.raises(ApprovalRequiredError, match="requires user approval"):
        await executor.execute(validated)


@pytest.mark.anyio
async def test_executor_handles_tool_failure():
    """Verify that tool execution exceptions are captured in ToolResult."""
    tool = MockTool("fail_tool", {"type": "object", "properties": {}})
    # Override execute to raise an exception
    tool.execute = AsyncMock(side_effect=Exception("Boom!"))

    call = ToolCall(name="fail_tool", arguments={})
    decision = PolicyDecision(
        decision=PolicyDecisionType.ALLOW,
        reason="Allowed",
        risk_level=ToolRiskLevel.LOW
    )
    validated = ValidatedToolCall(tool=tool, call=call, decision=decision)

    executor = ToolExecutor()
    result = await executor.execute(validated)

    assert result.success is False
    assert "An internal error occurred during tool execution." in result.error
