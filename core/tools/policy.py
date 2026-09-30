"""Policy and permission layer for Jarvis OS.

This module defines the authorization logic that determines whether a
validated tool call is permitted to execute. It follows a "deny-by-default"
security posture.
"""

from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass
from typing import Protocol, Mapping, Any

from core.agent.models import ToolCall
from core.tools.base import Tool


class PolicyDecisionType(Enum):
    """The final outcome of a policy evaluation."""
    ALLOW = auto()                # Execution permitted
    DENY = auto()                 # Execution strictly forbidden
    REQUIRE_USER_APPROVAL = auto() # Execution permitted only after explicit user consent


class ToolRiskLevel(Enum):
    """The intrinsic risk associated with a tool's capabilities."""
    LOW = auto()       # Read-only, non-sensitive
    MEDIUM = auto()    # Read-only, sensitive or low-impact write
    HIGH = auto()      # High-impact write or system change
    CRITICAL = auto()  # Potentially destructive or highly sensitive


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """The result of a policy engine evaluation."""
    decision: PolicyDecisionType
    reason: str
    risk_level: ToolRiskLevel


class PolicyEngine(Protocol):
    """Protocol for policy engines to allow for different implementations."""
    def authorize(self, tool: Tool, call: ToolCall) -> PolicyDecision:
        """Evaluate whether a tool call is permitted."""
        ...


class DefaultPolicyEngine:
    """A basic policy engine using a static risk map.

    Implements a "deny-by-default" posture: any tool not explicitly
    mapped to a risk level is treated as CRITICAL and denied.
    """

    def __init__(self, risk_map: Mapping[str, ToolRiskLevel] | None = None) -> None:
        # If no map is provided, we start with an empty one (Deny by Default)
        self._risk_map = risk_map or {}

    def authorize(self, tool: Tool, call: ToolCall) -> PolicyDecision:
        """Determine the authorization decision based on tool risk level."""
        # 1. Lookup risk level. Default to CRITICAL if not found.
        risk_level = self._risk_map.get(tool.name, ToolRiskLevel.CRITICAL)

        # 2. Map risk level to decision
        if risk_level == ToolRiskLevel.LOW:
            return PolicyDecision(
                decision=PolicyDecisionType.ALLOW,
                reason="Low risk tool",
                risk_level=risk_level,
            )

        if risk_level == ToolRiskLevel.MEDIUM:
            return PolicyDecision(
                decision=PolicyDecisionType.REQUIRE_USER_APPROVAL,
                reason="Medium risk tool requires user confirmation",
                risk_level=risk_level,
            )

        if risk_level == ToolRiskLevel.HIGH:
            return PolicyDecision(
                decision=PolicyDecisionType.REQUIRE_USER_APPROVAL,
                reason="High risk tool requires explicit user approval",
                risk_level=risk_level,
            )

        # CRITICAL or any other unhandled level
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reason=f"Tool {tool.name!r} is classified as CRITICAL risk and is forbidden",
            risk_level=risk_level,
        )
