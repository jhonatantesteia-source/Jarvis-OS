"""Tool invocation boundary for Jarvis OS.

This module provides the validation layer that sits between the Agent Runtime
(which proposes tool calls) and the Tool Executor (which executes them).
It ensures that tool requests are valid and authorized before execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from pydantic import create_model, ConfigDict, ValidationError

from core.agent.models import ToolCall
from core.tools.base import Tool
from core.tools.registry import ToolRegistry
from core.tools.policy import PolicyEngine, PolicyDecision, PolicyDecisionType
from core.tools.errors import (
    ToolValidationError,
    PolicyDeniedError,
    ApprovalRequiredError,
    ToolNotFoundError,
)


# Constants for supported JSON Schema subset to prevent silent failure/weakening
SUPPORTED_TOP_LEVEL_KEYWORDS = {"type", "properties", "required"}
SUPPORTED_PROP_KEYWORDS = {"type"}

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
            ToolValidationError: if the arguments are invalid or security identity is missing.
            PolicyDeniedError: if the policy engine explicitly denies the call.
        """
        # 0. Security Identity Check
        if not tool_call.internal_id:
            raise ToolValidationError("Security violation: Tool call missing internal security identity.")

        # 1. Lookup the tool in the registry
        tool = self._registry.get(tool_call.name)
        if tool is None:
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
        """Perform strict validation of arguments against the tool's schema.

        Uses Pydantic to enforce type safety, reject unknown arguments, and prevent coercion.
        Unsupported schema keywords result in a fail-closed ToolValidationError.
        """
        schema = tool.input_schema
        if not schema:
            return

        # 1. Validate top-level schema keywords
        for key in schema:
            if key not in SUPPORTED_TOP_LEVEL_KEYWORDS:
                raise ToolValidationError(
                    f"Unsupported schema keyword {key!r} in tool {tool.name!r}. Fail closed."
                )

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Map JSON schema types to Python types
        type_map = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "number": float,
            "object": dict,
        }

        try:
            # 2. Validate property-level schema keywords
            fields = {}
            for name, prop in properties.items():
                if not isinstance(prop, dict):
                    raise ToolValidationError(
                        f"Property {name!r} for tool {tool.name!r} must be a schema object."
                    )

                for key in prop:
                    if key not in SUPPORTED_PROP_KEYWORDS:
                        raise ToolValidationError(
                            f"Unsupported schema keyword {key!r} for argument {name!r} "
                            f"in tool {tool.name!r}. Fail closed."
                        )

                json_type = prop.get("type")
                if json_type not in type_map:
                    raise ToolValidationError(
                        f"Unsupported schema type {json_type!r} for argument {name!r} "
                        f"in tool {tool.name!r}. Fail closed."
                    )

                py_type = type_map[json_type]
                fields[name] = (py_type, ... if name in required else None)

            ValidationModel = create_model(
                f"{tool.name}Model",
                __config__=ConfigDict(extra="forbid", strict=True),
                **fields
            )

            ValidationModel(**arguments)
        except ValidationError as exc:
            # Extract a concise error message from Pydantic's error list
            error_detail = exc.errors()[0]
            loc = ".".join(map(str, error_detail["loc"]))
            msg = error_detail["msg"]
            raise ToolValidationError(f"Invalid argument {loc!r} for tool {tool.name!r}: {msg}")
        except ToolValidationError:
            raise
        except Exception as exc:
            raise ToolValidationError(f"Argument validation failed for tool {tool.name!r}: {exc}")
