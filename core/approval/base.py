"""Base abstractions for the Human-in-the-Loop authorization system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Mapping, Optional
from core.tools.policy import ToolRiskLevel

class ApprovalState(Enum):
    """The outcome of an approval request."""
    APPROVED = auto()
    DENIED = auto()
    EXPIRED = auto()
    UNAVAILABLE = auto()

@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """A structured request for human authorization."""
    request_id: str            # Unique identifier for the specific tool call
    tool_name: str             # Name of the tool being called
    arguments: Mapping[str, Any] # Exact validated arguments
    risk_level: ToolRiskLevel   # Risk level triggering the request
    reason: str                # Policy reason
    timestamp: float           # Creation time
    ttl: float = 300.0         # Time-to-live in seconds

@dataclass(frozen=True, slots=True)
class ApprovalGrant:
    """A single-use authorization token binding a decision to a specific action."""
    grant_id: str             # Unique ID for this grant
    request_id: str           # Linked to the original ToolCall id
    tool_name: str            # Bound tool
    arguments: Mapping[str, Any] # Bound arguments (exact match)
    expires_at: float          # Absolute expiration timestamp

@dataclass(frozen=True, slots=True)
class ApprovalResult:
    """The result of an approval request process."""
    request_id: str
    state: ApprovalState
    grant: Optional[ApprovalGrant] = None # Present only if state == APPROVED

class ApprovalProvider(ABC):
    """Interface for obtaining human authorization."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique identifier for this provider (e.g., 'cli')."""
        ...

    @abstractmethod
    async def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
        """
        Request a decision from the human.
        This is an async call that may suspend until a decision is made.
        """
        ...
