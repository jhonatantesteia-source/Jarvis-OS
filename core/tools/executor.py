"""Tool executor for Jarvis OS.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Set

from core.tools.base import ToolResult
from core.tools.boundary import ValidatedToolCall
from core.tools.errors import get_safe_error_message, ApprovalRequiredError
from core.tools.policy import PolicyDecisionType
from core.approval.base import ApprovalGrant
from core.approval.errors import AuthorizationError, ApprovalReplayError, ApprovalExpiredError
from core.tools.audit import SecurityAuditLogger

class ToolExecutor:
    """Executor that runs authorized tool calls.
    """

    def __init__(self, audit_logger: SecurityAuditLogger | None = None) -> None:
        self._consumed_grant_ids: Set[str] = set()
        self._lock = asyncio.Lock()
        self._audit_logger = audit_logger

    async def execute(
        self,
        validated_call: ValidatedToolCall,
        grant: ApprovalGrant | None = None
    ) -> ToolResult:
        """Execute a validated tool call.

        Args:
            validated_call: A tool call that has passed through the boundary.
            grant: An optional authorization grant for tools requiring approval.

        Returns:
            The result of the tool execution.

        Raises:
            ApprovalRequiredError: If the policy requires approval but no grant was provided.
            AuthorizationError: If the grant is invalid, expired, or a replay.
        """
        decision_type = validated_call.decision.decision

        # 1. Policy Enforcement
        if decision_type == PolicyDecisionType.DENY:
            if self._audit_logger:
                self._audit_logger.log_event(
                    SecurityAuditLogger.EXECUTION_DENIED,
                    validated_call.call.internal_id,
                    validated_call.tool.name,
                    "DENIED",
                    "Strictly forbidden by policy",
                )
            return ToolResult(
                success=False,
                error=f"Tool {validated_call.tool.name!r} is strictly forbidden by policy."
            )

        if decision_type == PolicyDecisionType.REQUIRE_USER_APPROVAL:
            # Authorization Gate
            if grant is None:
                raise ApprovalRequiredError(
                    f"Tool {validated_call.tool.name!r} requires user approval to execute."
                )

            await self._validate_grant(grant, validated_call)

        # 2. Execute the tool
        try:
            if self._audit_logger:
                self._audit_logger.log_event(
                    SecurityAuditLogger.EXECUTION_AUTHORIZED,
                    validated_call.call.internal_id,
                    validated_call.tool.name,
                    "AUTHORIZED",
                    "Authorization boundary passed",
                )
            return await validated_call.tool.execute(**validated_call.call.arguments)
        except Exception as exc:
            if self._audit_logger:
                self._audit_logger.log_event(
                    SecurityAuditLogger.EXECUTION_FAILED,
                    validated_call.call.internal_id,
                    validated_call.tool.name,
                    "FAILED",
                    get_safe_error_message(exc),
                )
            return ToolResult(
                success=False,
                error=get_safe_error_message(exc)
            )

    async def _validate_grant(self, grant: ApprovalGrant, validated_call: ValidatedToolCall) -> None:
        """Performs strict binding and replay checks on the grant.
        """
        # A. Binding: Tool Name
        if grant.tool_name != validated_call.tool.name:
            if self._audit_logger:
                self._audit_logger.log_event(
                    SecurityAuditLogger.EXECUTION_DENIED,
                    validated_call.call.internal_id,
                    validated_call.tool.name,
                    "DENIED",
                    "Grant tool name mismatch",
                )
            raise AuthorizationError("Authorization grant is bound to a different tool.")

        # B. Binding: Arguments
        if grant.arguments != validated_call.call.arguments:
            if self._audit_logger:
                self._audit_logger.log_event(
                    SecurityAuditLogger.EXECUTION_DENIED,
                    validated_call.call.internal_id,
                    validated_call.tool.name,
                    "DENIED",
                    "Grant arguments mismatch",
                )
            raise AuthorizationError("Authorization grant arguments do not match the call.")

        # C. Binding: Request Identity
        if grant.request_id != validated_call.call.internal_id:
            if self._audit_logger:
                self._audit_logger.log_event(
                    SecurityAuditLogger.EXECUTION_DENIED,
                    validated_call.call.internal_id,
                    validated_call.tool.name,
                    "DENIED",
                    "Grant request ID mismatch",
                )
            raise AuthorizationError("Authorization grant is bound to a different request.")

        # D. Expiration
        if time.time() >= grant.expires_at:
            if self._audit_logger:
                self._audit_logger.log_event(
                    SecurityAuditLogger.APPROVAL_EXPIRED,
                    validated_call.call.internal_id,
                    validated_call.tool.name,
                    "EXPIRED",
                    "Grant expiration timestamp reached",
                )
            raise ApprovalExpiredError("The authorization grant has expired.")

        # E. Replay Protection (Atomic Check-and-Consume)
        async with self._lock:
            if grant.grant_id in self._consumed_grant_ids:
                if self._audit_logger:
                    self._audit_logger.log_event(
                        SecurityAuditLogger.APPROVAL_REPLAYED,
                        validated_call.call.internal_id,
                        validated_call.tool.name,
                        "REPLAYED",
                        "Grant already consumed",
                    )
                raise ApprovalReplayError("This authorization grant has already been consumed.")
            self._consumed_grant_ids.add(grant.grant_id)
