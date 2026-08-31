"""Tool executor for Jarvis OS.

This module provides the execution layer that performs the actual tool invocation.
It only executes calls that have already been validated and authorized by the
ToolInvocationBoundary.
"""

from __future__ import annotations

from typing import Any
from core.tools.base import ToolResult
from core.tools.boundary import ValidatedToolCall, ApprovalRequiredError
from core.tools.policy import PolicyDecisionType


class ToolExecutor:
    """Executor that runs authorized tool calls."""

    async def execute(
        self,
        validated_call: ValidatedToolCall,
        approved: bool = False
    ) -> ToolResult:
        """Execute a validated tool call.

        Args:
            validated_call: A tool call that has passed through the boundary.
            approved: Whether explicit user approval has been granted.

        Returns:
            The result of the tool execution.

        Raises:
            ApprovalRequiredError: If the policy requires approval but none was provided.
        """
        decision_type = validated_call.decision.decision

        # 1. Check if approval is required but not provided
        if decision_type == PolicyDecisionType.REQUIRE_USER_APPROVAL and not approved:
            raise ApprovalRequiredError(
                f"Tool {validated_call.tool.name!r} requires user approval to execute. "
                f"Reason: {validated_call.decision.reason}"
            )

        # 2. Execute the tool
        # Note: PolicyDeniedError is handled at the Boundary, so we only reach here
        # if the decision is ALLOW or REQUIRE_USER_APPROVAL (and approved).
        try:
            return await validated_call.tool.execute(**validated_call.call.arguments)
        except Exception as exc:
            # Wrap unexpected exceptions in a ToolResult failure
            return ToolResult(
                success=False,
                error=f"Unexpected error during tool execution: {str(exc)}"
            )
