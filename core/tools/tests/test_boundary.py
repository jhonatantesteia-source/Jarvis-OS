import pytest
from unittest.mock import MagicMock

from core.agent.models import ToolCall
from core.agent.runtime import ToolNotFoundError
from core.tools.base import Tool
from core.tools.boundary import (
    ToolInvocationBoundary,
    ToolValidationError,
    ValidatedToolCall,
    PolicyDeniedError,
)
from core.tools.registry import ToolRegistry
from core.tools.policy import PolicyEngine, PolicyDecision, PolicyDecisionType, ToolRiskLevel


class MockTool(Tool):
    """A tool for testing the boundary."""

    def __init__(self, name: str, schema: dict):
        self._name = name
        self._schema = schema

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Mock tool description"

    @property
    def input_schema(self) -> dict:
        return self._schema

    async def execute(self, **kwargs):
        return None # Not used in boundary tests


@pytest.mark.anyio
async def test_valid_tool_lookup():
    """Verify that a registered tool can be resolved and authorized."""
    registry = ToolRegistry()
    tool = MockTool("test_tool", {"type": "object", "properties": {}})
    registry.register(tool)

    # Mock policy to allow the tool
    policy = MagicMock(spec=PolicyEngine)
    policy.authorize.return_value = PolicyDecision(
        decision=PolicyDecisionType.ALLOW,
        reason="Allowed",
        risk_level=ToolRiskLevel.LOW
    )

    boundary = ToolInvocationBoundary(registry, policy)
    call = ToolCall(name="test_tool", arguments={}, internal_id="test_id")

    validated = await boundary.validate(call)

    assert isinstance(validated, ValidatedToolCall)
    assert validated.tool == tool
    assert validated.call == call
    assert validated.decision.decision == PolicyDecisionType.ALLOW


@pytest.mark.anyio
async def test_unknown_tool_lookup():
    """Verify that an unknown tool produces a controlled error."""
    registry = ToolRegistry()
    policy = MagicMock(spec=PolicyEngine)
    boundary = ToolInvocationBoundary(registry, policy)
    call = ToolCall(name="unknown_tool", arguments={}, internal_id="test_id")

    with pytest.raises(ToolNotFoundError, match="Tool not found in registry"):
        await boundary.validate(call)


@pytest.mark.anyio
async def test_argument_validation_missing_required():
    """Verify that missing required arguments are rejected."""
    registry = ToolRegistry()
    schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"]
    }
    tool = MockTool("test_tool", schema)
    registry.register(tool)

    policy = MagicMock(spec=PolicyEngine)
    boundary = ToolInvocationBoundary(registry, policy)
    call = ToolCall(name="test_tool", arguments={}, internal_id="test_id") # missing 'text'

    with pytest.raises(ToolValidationError, match="Field required"):
        await boundary.validate(call)


@pytest.mark.anyio
async def test_argument_validation_wrong_type():
    """Verify that malformed tool arguments are rejected."""
    registry = ToolRegistry()
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
    }
    tool = MockTool("test_tool", schema)
    registry.register(tool)

    policy = MagicMock(spec=PolicyEngine)
    boundary = ToolInvocationBoundary(registry, policy)
    call = ToolCall(name="test_tool", arguments={"count": "not-an-int"}, internal_id="test_id")

    with pytest.raises(ToolValidationError, match="Input should be a valid integer"):
        await boundary.validate(call)


@pytest.mark.anyio
async def test_argument_validation_unknown_argument():
    """Verify that unknown arguments are strictly rejected."""
    registry = ToolRegistry()
    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
    }
    tool = MockTool("test_tool", schema)
    registry.register(tool)

    policy = MagicMock(spec=PolicyEngine)
    boundary = ToolInvocationBoundary(registry, policy)
    call = ToolCall(name="test_tool", arguments={"query": "weather", "unexpected": True}, internal_id="test_id")

    with pytest.raises(ToolValidationError, match="Extra inputs are not permitted"):
        await boundary.validate(call)


@pytest.mark.anyio
async def test_no_execution_guarantee():
    """
    Verify that validating a tool call does NOT execute the tool.
    This is the mandatory security test.
    """
    class SideEffectTool(MockTool):
        def __init__(self, name, schema):
            super().__init__(name, schema)
            self.executed = False

        async def execute(self, **kwargs):
            self.executed = True
            return None

    registry = ToolRegistry()
    tool = SideEffectTool("risky_tool", {"type": "object", "properties": {}})
    registry.register(tool)

    policy = MagicMock(spec=PolicyEngine)
    policy.authorize.return_value = PolicyDecision(
        decision=PolicyDecisionType.ALLOW,
        reason="Allowed",
        risk_level=ToolRiskLevel.LOW
    )
    boundary = ToolInvocationBoundary(registry, policy)
    call = ToolCall(name="risky_tool", arguments={}, internal_id="test_id")

    # Validate the tool call
    await boundary.validate(call)

    # Verify the tool was NOT executed
    assert tool.executed is False, "Tool was executed during validation!"


@pytest.mark.anyio
async def test_policy_deny():
    """Verify that a denied tool call raises PolicyDeniedError."""
    registry = ToolRegistry()
    tool = MockTool("denied_tool", {"type": "object", "properties": {}})
    registry.register(tool)

    policy = MagicMock(spec=PolicyEngine)
    policy.authorize.return_value = PolicyDecision(
        decision=PolicyDecisionType.DENY,
        reason="Forbidden",
        risk_level=ToolRiskLevel.CRITICAL
    )

    boundary = ToolInvocationBoundary(registry, policy)
    call = ToolCall(name="denied_tool", arguments={}, internal_id="test_id")

    with pytest.raises(PolicyDeniedError, match="denied by policy: Forbidden"):
        await boundary.validate(call)


@pytest.mark.anyio
async def test_policy_require_approval():
    """Verify that a tool requiring approval is marked as such in the result."""
    registry = ToolRegistry()
    tool = MockTool("approval_tool", {"type": "object", "properties": {}})
    registry.register(tool)

    policy = MagicMock(spec=PolicyEngine)
    policy.authorize.return_value = PolicyDecision(
        decision=PolicyDecisionType.REQUIRE_USER_APPROVAL,
        reason="Approval needed",
        risk_level=ToolRiskLevel.HIGH
    )

    boundary = ToolInvocationBoundary(registry, policy)
    call = ToolCall(name="approval_tool", arguments={}, internal_id="test_id")

    validated = await boundary.validate(call)
    assert validated.decision.decision == PolicyDecisionType.REQUIRE_USER_APPROVAL
    assert validated.decision.reason == "Approval needed"

