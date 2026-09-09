import pytest
from core.agent.models import ToolCall
from core.tools.base import Tool, ToolResult
from core.tools.registry import ToolRegistry
from core.tools.boundary import ToolInvocationBoundary
from core.tools.policy import DefaultPolicyEngine, ToolRiskLevel
from core.tools.executor import ToolExecutor
from core.tools.boundary import PolicyDeniedError, ApprovalRequiredError


class MockTool(Tool):
    """A tool for integration testing."""

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
        return ToolResult(success=True, content=f"Result from {self.name}")


@pytest.fixture
def setup_system():
    """Sets up the tool system with a default policy."""
    registry = ToolRegistry()
    # Low risk tool
    tool_low = MockTool("low_risk", {"type": "object", "properties": {}})
    # Medium risk tool
    tool_med = MockTool("med_risk", {"type": "object", "properties": {}})
    # Critical risk tool
    tool_crit = MockTool("crit_risk", {"type": "object", "properties": {}})

    registry.register(tool_low)
    registry.register(tool_med)
    registry.register(tool_crit)

    risk_map = {
        "low_risk": ToolRiskLevel.LOW,
        "med_risk": ToolRiskLevel.MEDIUM,
        "crit_risk": ToolRiskLevel.CRITICAL,
    }
    policy = DefaultPolicyEngine(risk_map=risk_map)
    boundary = ToolInvocationBoundary(registry, policy)
    executor = ToolExecutor()

    return boundary, executor


@pytest.mark.anyio
async def test_full_flow_allow(setup_system):
    """Prove the path: ToolCall -> Boundary -> Policy -> Executor -> ToolResult (ALLOW)."""
    boundary, executor = setup_system
    call = ToolCall(name="low_risk", arguments={})

    # 1. Boundary validation
    validated = await boundary.validate(call)
    # 2. Execution
    result = await executor.execute(validated)

    assert result.success is True
    assert "Result from low_risk" in result.content


@pytest.mark.anyio
async def test_full_flow_deny(setup_system):
    """Prove that a denied tool never reaches the executor."""
    boundary, executor = setup_system
    call = ToolCall(name="crit_risk", arguments={})

    with pytest.raises(PolicyDeniedError):
        await boundary.validate(call)

    # In a real system, we wouldn't even have a 'validated' object to pass to the executor.


@pytest.mark.anyio
async def test_full_flow_approval_required(setup_system):
    """Prove that a tool requiring approval is blocked by the executor unless approved."""
    boundary, executor = setup_system
    call = ToolCall(name="med_risk", arguments={}, id="call_1")

    # 1. Boundary validation (should pass but mark as requiring approval)
    validated = await boundary.validate(call)

    # 2. Execution without approval (should fail)
    with pytest.raises(ApprovalRequiredError):
        await executor.execute(validated)

    # 3. Execution with approval (should succeed)
    from core.approval.base import ApprovalGrant
    import time
    grant = ApprovalGrant(
        grant_id="g1", request_id="call_1", tool_name="med_risk",
        arguments={}, expires_at=time.time() + 100
    )
    result = await executor.execute(validated, grant=grant)
    assert result.success is True
    assert "Result from med_risk" in result.content
