"""Tool invocation boundary for Jarvis OS.

This module provides the validation layer that sits between the Agent Runtime
(which proposes tool calls) and the Tool Executor (which executes them).
It ensures that tool requests are valid and authorized before execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.agent.models import ToolCall
from core.agent.errors import AgentError
from core.tools.base import Tool
from core.tools.registry import ToolRegistry
from core.tools.policy import PolicyEngine, PolicyDecision, PolicyDecisionType


class ToolValidationError(AgentError):
    """Raised when a tool call fails validation."""


class PolicyDeniedError(AgentError):
    """Raised when a tool call is explicitly denied by the policy engine."""


class ApprovalRequiredError(AgentError):
    """Raised when a tool call requires user approval but none was provided."""


@dataclass(frozen=True, slots=True)
class ValidatedToolCall:
    """A tool call that has been validated against the registry, schema, and policy."""

    tool: Tool
    call: ToolCall
    decision: PolicyDecision


class ToolInvocationBoundary:
    """Boundary that validates tool calls before they reach the executor."""

    def __init__(self, registry: ToolRegistry, policy_engine: PolicyEngine) -> None:
        self._registry = registry
        self._policy_engine = policy_engine

    async def validate(self, tool_call: ToolCall) -> ValidatedToolCall:
        """Validate a tool call against the registry, the tool's schema, and policy.

        Args:
            tool_call: The proposed tool invocation.

        Returns:
            A ValidatedToolCall containing the resolved Tool object and policy decision.

        Raises:
            ToolNotFoundError: if the tool name is not registered.
            ToolValidationError: if the arguments are invalid.
            PolicyDeniedError: if the policy engine explicitly denies the call.
        """
        # 1. Lookup the tool in the registry
        tool = self._registry.get(tool_call.name)
        if tool is None:
            from core.agent.runtime import ToolNotFoundError
            raise ToolNotFoundError(f"Tool not found in registry: {tool_call.name!r}")

        # 2. Validate arguments against the tool's input schema
        self._validate_arguments(tool, tool_call.arguments)

        # 3. Evaluate policy
        decision = self._policy_engine.authorize(tool, tool_call)

        if decision.decision == PolicyDecisionType.DENY:
            raise PolicyDeniedError(
                f"Tool {tool.name!r} was denied by policy: {decision.reason}"
            )

        return ValidatedToolCall(
            tool=tool,
            call=tool_call,
            decision=decision,
        )

    def _validate_arguments(self, tool: Tool, arguments: Mapping[str, Any]) -> None:
        """Perform basic validation of arguments against the tool's schema."""
        schema = tool.input_schema
        if not schema:
            return

        # Basic JSON Schema-like validation
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Check for missing required arguments
        for req in required:
            if req not in arguments:
                raise ToolValidationError(
                    f"Tool {tool.name!r} is missing required argument: {req!r}"
                )

        # Basic type checking for provided arguments
        for key, value in arguments.items():
            if key not in properties:
                # We'll allow extra arguments for now, but a stricter policy
                # could reject them.
                continue

            expected_type = properties[key].get("type")
            if expected_type == "string" and not isinstance(value, str):
                raise ToolValidationError(
                    f"Argument {key!r} for tool {tool.name!r} must be a string, "
                    f"got {type(value).__name__}"
                )
            elif expected_type == "integer" and not isinstance(value, int):
                raise ToolValidationError(
                    f"Argument {key!r} for tool {tool.name!r} must be an integer, "
                    f"got {type(value).__name__}"
                )
            elif expected_type == "boolean" and not isinstance(value, bool):
                raise ToolValidationError(
                    f"Argument {key!r} for tool {tool.name!r} must be a boolean, "
                    f"got {type(value).__name__}"
                )
