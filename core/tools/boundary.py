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


class ToolValidationError(AgentError):
    """Raised when a tool call fails validation."""


@dataclass(frozen=True, slots=True)
class ValidatedToolCall:
    """A tool call that has been validated against the registry and schema."""

    tool: Tool
    call: ToolCall


class ToolInvocationBoundary:
    """Boundary that validates tool calls before they reach the executor."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def validate(self, tool_call: ToolCall) -> ValidatedToolCall:
        """Validate a tool call against the registry and the tool's schema.

        Args:
            tool_call: The proposed tool invocation.

        Returns:
            A ValidatedToolCall containing the resolved Tool object.

        Raises:
            ToolNotFoundError: if the tool name is not registered.
            ToolValidationError: if the arguments are invalid.
        """
        # 1. Lookup the tool in the registry
        tool = self._registry.get(tool_call.name)
        if tool is None:
            # We reuse ToolNotFoundError from core.agent (or define it here)
            # For now, we'll use the one defined in agent.runtime or a generic one.
            # Let's check core.agent.runtime.ToolNotFoundError
            from core.agent.runtime import ToolNotFoundError
            raise ToolNotFoundError(f"Tool not found in registry: {tool_call.name!r}")

        # 2. Validate arguments against the tool's input schema
        self._validate_arguments(tool, tool_call.arguments)

        return ValidatedToolCall(tool=tool, call=tool_call)

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
