import pytest

from core.agent.models import ToolCall
from core.agent.runtime import ToolNotFoundError
from core.tools.base import Tool
from core.tools.boundary import ToolInvocationBoundary, ToolValidationError, ValidatedToolCall
from core.tools.registry import ToolRegistry


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
    """Verify that a registered tool can be resolved."""
    registry = ToolRegistry()
    tool = MockTool("test_tool", {"type": "object", "properties": {}})
    registry.register(tool)

    boundary = ToolInvocationBoundary(registry)
    call = ToolCall(name="test_tool", arguments={})

    validated = await boundary.validate(call)

    assert isinstance(validated, ValidatedToolCall)
    assert validated.tool == tool
    assert validated.call == call


@pytest.mark.anyio
async def test_unknown_tool_lookup():
    """Verify that an unknown tool produces a controlled error."""
    registry = ToolRegistry()
    boundary = ToolInvocationBoundary(registry)
    call = ToolCall(name="unknown_tool", arguments={})

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

    boundary = ToolInvocationBoundary(registry)
    call = ToolCall(name="test_tool", arguments={}) # missing 'text'

    with pytest.raises(ToolValidationError, match="missing required argument: 'text'"):
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

    boundary = ToolInvocationBoundary(registry)
    call = ToolCall(name="test_tool", arguments={"count": "not-an-int"})

    with pytest.raises(ToolValidationError, match="must be an integer"):
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

    boundary = ToolInvocationBoundary(registry)
    call = ToolCall(name="risky_tool", arguments={})

    # Validate the tool call
    await boundary.validate(call)

    # Verify the tool was NOT executed
    assert tool.executed is False, "Tool was executed during validation!"
