import pytest
from unittest.mock import MagicMock
import time
import uuid

from core.agent.models import ToolCall
from core.agent.runtime import AgentRuntime
from core.tools.base import Tool, ToolResult
from core.tools.boundary import (
    ToolInvocationBoundary,
    ToolValidationError,
    ValidatedToolCall,
)
from core.tools.registry import ToolRegistry
from core.tools.policy import PolicyEngine, PolicyDecision, PolicyDecisionType, ToolRiskLevel
from core.tools.executor import ToolExecutor
from core.approval.base import ApprovalGrant

class MockTool(Tool):
    def __init__(self, name, schema):
        self._name = name
        self._schema = schema
        self.call_count = 0
    @property
    def name(self) -> str: return self._name
    @property
    def description(self) -> str: return "Mock Tool"
    @property
    def input_schema(self) -> dict: return self._schema
    async def execute(self, **kwargs):
        self.call_count += 1
        return ToolResult(success=True, content="success")

@pytest.fixture
def setup_boundary():
    registry = ToolRegistry()
    policy = MagicMock(spec=PolicyEngine)
    policy.authorize.return_value = PolicyDecision(
        decision=PolicyDecisionType.ALLOW,
        reason="Allowed",
        risk_level=ToolRiskLevel.LOW
    )
    boundary = ToolInvocationBoundary(registry, policy)
    return boundary, registry, policy

@pytest.mark.anyio
async def test_p0_1_runtime_generates_internal_id():
    # Test A: Runtime generates internal ID and it's different from provider ID
    from core.llm import LLMResponse
    from core.llm import LLMProvider

    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.complete.return_value = LLMResponse(
        content="",
        model="test",
        tool_calls=[{"id": "provider_call_123", "name": "test_tool", "arguments": {}}]
    )

    registry = ToolRegistry()
    boundary = ToolInvocationBoundary(registry, MagicMock())
    executor = ToolExecutor()
    runtime = AgentRuntime(mock_provider, registry, boundary, executor)

    # Trigger tool call extraction
    response = LLMResponse(
        content="",
        model="test",
        tool_calls=[{"id": "provider_call_123", "name": "test_tool", "arguments": {}}]
    )

    tool_calls = AgentRuntime._extract_tool_calls(response, round_number=1)

    tc = tool_calls[0]
    assert tc.id == "provider_call_123"
    assert tc.internal_id is not None
    assert tc.internal_id != "provider_call_123"

@pytest.mark.anyio
async def test_p0_1_internal_id_uniqueness():
    # Test B: Internal IDs are unique for different calls in same response
    from core.llm import LLMResponse

    response = LLMResponse(
        content="",
        model="test",
        tool_calls=[
            {"id": "id1", "name": "tool1", "arguments": {}},
            {"id": "id2", "name": "tool2", "arguments": {}},
        ]
    )

    tool_calls = AgentRuntime._extract_tool_calls(response, round_number=1)
    assert tool_calls[0].internal_id != tool_calls[1].internal_id

@pytest.mark.anyio
async def test_p0_1_missing_internal_id_fails_closed(setup_boundary):
    # Test C: Missing internal ID cannot cross authorization boundary
    boundary, registry, _ = setup_boundary

    # Construct ToolCall without internal_id (manually bypassing type hint)
    # We use a workaround because dataclass might not allow None if typed as str
    # but for the test we force it.
    class BadToolCall(ToolCall):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    call = ToolCall(name="test_tool", arguments={}, id="id1", internal_id=None) # type: ignore

    with pytest.raises(ToolValidationError, match="Security violation: Tool call missing internal security identity"):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_1_provider_id_cannot_authorize(setup_boundary):
    # Test D: Provider ID cannot authorize a grant
    boundary, registry, policy = setup_boundary
    tool = MockTool("test_tool", {"type": "object", "properties": {}})
    registry.register(tool)

    call = ToolCall(name="test_tool", arguments={}, id="provider_id", internal_id="internal_id")

    # Must require approval for the grant to be checked
    policy.authorize.return_value = PolicyDecision(
        decision=PolicyDecisionType.REQUIRE_USER_APPROVAL,
        reason="Approval needed",
        risk_level=ToolRiskLevel.HIGH
    )

    validated = await boundary.validate(call)

    executor = ToolExecutor()
    grant = ApprovalGrant(
        grant_id="g1",
        request_id="provider_id", # WRONG: should be internal_id
        tool_name="test_tool",
        arguments={},
        expires_at=time.time() + 100
    )

    from core.approval.errors import AuthorizationError
    with pytest.raises(AuthorizationError, match="bound to a different request"):
        await executor.execute(validated, grant=grant)

@pytest.mark.anyio
async def test_p0_1_valid_internal_id_authorizes(setup_boundary):
    # Test E: Valid internal ID authorizes correctly
    boundary, registry, policy = setup_boundary
    tool = MockTool("test_tool", {"type": "object", "properties": {}})
    registry.register(tool)

    call = ToolCall(name="test_tool", arguments={}, id="provider_id", internal_id="internal_id")
    validated = await boundary.validate(call)

    executor = ToolExecutor()
    grant = ApprovalGrant(
        grant_id="g1",
        request_id="internal_id", # CORRECT
        tool_name="test_tool",
        arguments={},
        expires_at=time.time() + 100
    )

    result = await executor.execute(validated, grant=grant)
    assert result.success is True

@pytest.mark.anyio
async def test_p0_2_unknown_argument(setup_boundary):
    # Test A: Unknown argument rejected
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    })
    registry.register(tool)

    call = ToolCall(name="test_tool", arguments={"name": "John", "unexpected": "value"}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Extra inputs are not permitted"):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_missing_required(setup_boundary):
    # Test B: Missing required argument rejected
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    })
    registry.register(tool)

    call = ToolCall(name="test_tool", arguments={}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Field required"):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_wrong_primitive_type(setup_boundary):
    # Test C: Wrong primitive type rejected
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {"age": {"type": "integer"}}
    })
    registry.register(tool)

    call = ToolCall(name="test_tool", arguments={"age": "not-an-integer"}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Input should be a valid integer"):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_coercion_attempt(setup_boundary):
    # Test D: Coercion attempt rejected (Strict mode)
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {"age": {"type": "integer"}}
    })
    registry.register(tool)

    call = ToolCall(name="test_tool", arguments={"age": "42"}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Input should be a valid integer"):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_unsupported_feature(setup_boundary):
    # Test E: Unsupported schema feature fails closed
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {"data": {"type": "array"}} # array not in our type_map
    })
    registry.register(tool)

    call = ToolCall(name="test_tool", arguments={"data": [1, 2]}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Unsupported schema type 'array'"):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_validation_before_policy(setup_boundary):
    # Test G: Validation occurs before policy
    boundary, registry, policy = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    })
    registry.register(tool)

    call = ToolCall(name="test_tool", arguments={}, internal_id="int1") # Missing 'name'

    with pytest.raises(ToolValidationError):
        await boundary.validate(call)

    policy.authorize.assert_not_called()

@pytest.mark.anyio
async def test_p0_2_validation_failure_no_execution(setup_boundary):
    # Test H: Validation failure cannot execute tool
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    })
    registry.register(tool)

    call = ToolCall(name="test_tool", arguments={}, internal_id="int1")

    try:
        await boundary.validate(call)
    except ToolValidationError:
        pass

    assert tool.call_count == 0

@pytest.mark.anyio
async def test_p0_2_unsupported_top_level_keyword(setup_boundary):
    """Verify that unsupported top-level schema keywords cause fail-closed rejection."""
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {},
        "unexpected_keyword": "value"
    })
    registry.register(tool)
    
    call = ToolCall(name="test_tool", arguments={}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Unsupported schema keyword 'unexpected_keyword' in tool 'test_tool'. Fail closed."):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_unsupported_prop_keyword(setup_boundary):
    """Verify that unsupported property-level schema keywords cause fail-closed rejection."""
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 10}
        }
    })
    registry.register(tool)
    
    call = ToolCall(name="test_tool", arguments={"name": "too-short"}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Unsupported schema keyword 'minLength' for argument 'name' in tool 'test_tool'. Fail closed."):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_unsupported_enum_keyword(setup_boundary):
    """Verify that unsupported 'enum' keyword cause fail-closed rejection."""
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {
            "role": {"type": "string", "enum": ["admin", "user"]}
        }
    })
    registry.register(tool)
    
    call = ToolCall(name="test_tool", arguments={"role": "admin"}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Unsupported schema keyword 'enum' for argument 'role' in tool 'test_tool'. Fail closed."):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_unsupported_numeric_constraint(setup_boundary):
    """Verify that unsupported numeric constraints cause fail-closed rejection."""
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {
            "age": {"type": "integer", "minimum": 1}
        }
    })
    registry.register(tool)
    
    call = ToolCall(name="test_tool", arguments={"age": 25}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Unsupported schema keyword 'minimum' for argument 'age' in tool 'test_tool'. Fail closed."):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_unsupported_nested_schema(setup_boundary):
    """Verify that unsupported nested schemas (properties in object) fail closed."""
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {
            "meta": {
                "type": "object",
                "properties": {"key": {"type": "string"}}
            }
        }
    })
    registry.register(tool)
    
    call = ToolCall(name="test_tool", arguments={"meta": {"key": "val"}}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="Unsupported schema keyword 'properties' for argument 'meta' in tool 'test_tool'. Fail closed."):
        await boundary.validate(call)

@pytest.mark.anyio
async def test_p0_2_supported_primitive_still_works(setup_boundary):
    """Verify that existing valid primitive schemas still work."""
    boundary, registry, _ = setup_boundary
    tool = MockTool("test_tool", {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "active": {"type": "boolean"},
            "score": {"type": "number"}
        }
    })
    registry.register(tool)
    
    call = ToolCall(name="test_tool", arguments={"name": "Jarvis", "age": 1, "active": True, "score": 95.5}, internal_id="int1")
    validated = await boundary.validate(call)
    assert validated.tool.name == "test_tool"

@pytest.mark.anyio
async def test_p0_2_schema_structure_validation(setup_boundary):
    """Verify that the tool schema structure itself is validated before argument validation."""
    boundary, registry, _ = setup_boundary
    
    # 1. Schema must be a mapping
    tool_not_dict = MockTool("not_dict", "not-a-dict") # type: ignore
    registry.register(tool_not_dict)
    call = ToolCall(name="not_dict", arguments={}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="must be a mapping"):
        await boundary.validate(call)
    
    # 2. Type must be 'object'
    tool_wrong_type = MockTool("wrong_type", {"type": "array"})
    registry.register(tool_wrong_type)
    call = ToolCall(name="wrong_type", arguments={}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="must be 'object'"):
        await boundary.validate(call)
        
    # 3. Properties must be a mapping
    tool_wrong_props = MockTool("wrong_props", {"type": "object", "properties": []})
    registry.register(tool_wrong_props)
    call = ToolCall(name="wrong_props", arguments={}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="must be a mapping"):
        await boundary.validate(call)
        
    # 4. Required must be list of strings
    tool_wrong_req = MockTool("wrong_req", {"type": "object", "required": "not-a-list"})
    registry.register(tool_wrong_req)
    call = ToolCall(name="wrong_req", arguments={}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="must be a list of strings"):
        await boundary.validate(call)
        
    # 5. Required fields must exist in properties
    tool_missing_prop = MockTool("missing_prop", {
        "type": "object", 
        "properties": {"a": {"type": "string"}},
        "required": ["b"]
    })
    registry.register(tool_missing_prop)
    call = ToolCall(name="missing_prop", arguments={"a": "val"}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="is not defined in properties"):
        await boundary.validate(call)

    # 6. Property names must be strings
    # This is hard to trigger with a dict literal, but we can use a custom dict
    class BadDict(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self[123] = {"type": "string"}
            
    tool_bad_prop_name = MockTool("bad_prop_name", {"type": "object", "properties": BadDict()})
    registry.register(tool_bad_prop_name)
    call = ToolCall(name="bad_prop_name", arguments={}, internal_id="int1")
    with pytest.raises(ToolValidationError, match="must be a string"):
        await boundary.validate(call)
