"""Security auditing for Jarvis OS.

This module provides mechanisms for logging security-critical events related
to tool authorization and execution.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Mapping

from core.logging.logger import logger
from core.events.bus import EventBus

@dataclass(frozen=True, slots=True)
class SecurityEvent:
    """A structured security audit event."""
    event_type: str
    timestamp: float
    invocation_id: str
    tool_name: str
    decision: str
    reason: str
    metadata: Mapping[str, Any] = None

class SecurityAuditLogger:
    """Logger for security-critical authorization and execution events.
    """

    # Event Types
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_DENIED = "approval.denied"
    APPROVAL_EXPIRED = "approval.expired"
    APPROVAL_REPLAYED = "approval.replayed"
    EXECUTION_AUTHORIZED = "tool.execution.authorized"
    EXECUTION_DENIED = "tool.execution.denied"
    EXECUTION_FAILED = "tool.execution.failed"

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus

    def log_event(
        self,
        event_type: str,
        invocation_id: str,
        tool_name: str,
        decision: str,
        reason: str,
        **metadata: Any
    ) -> None:
        """Logs a security event to the system log and optionally the event bus."""
        event = SecurityEvent(
            event_type=event_type,
            timestamp=datetime.now().timestamp(),
            invocation_id=invocation_id,
            tool_name=tool_name,
            decision=decision,
            reason=reason,
            metadata=metadata,
        )

        # 1. Persistent log via loguru wrapper
        logger.info(
            f"[SECURITY] {event.event_type} | ID: {event.invocation_id} | "
            f"Tool: {event.tool_name} | Decision: {event.decision} | Reason: {event.reason} | "
            f"Meta: {event.metadata}"
        )

        # 2. Event propagation via EventBus
        if self._event_bus:
            self._event_bus.publish(f"security.{event.event_type}", asdict(event))
