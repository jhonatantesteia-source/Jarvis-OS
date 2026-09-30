"""Deterministic fake approval provider for testing.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence
import uuid
import time

from core.approval.base import (
    ApprovalProvider,
    ApprovalRequest,
    ApprovalResult,
    ApprovalState,
    ApprovalGrant
)

class FakeApprovalProvider(ApprovalProvider):
    """A provider that returns scripted outcomes for deterministic tests.
    """

    def __init__(self):
        self._outcomes: Mapping[str, ApprovalState] = {}
        self._custom_grants: Mapping[str, ApprovalGrant] = {}
        self.request_history: list[ApprovalRequest] = []

    @property
    def name(self) -> str:
        return "fake"

    def set_outcome(self, request_id: str, state: ApprovalState, grant: ApprovalGrant | None = None):
        """Configure the outcome for a specific request ID."""
        self._outcomes[request_id] = state
        if grant:
            self._custom_grants[request_id] = grant

    async def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
        self.request_history.append(request)

        state = self._outcomes.get(request.request_id, ApprovalState.DENIED)

        grant = None
        if state == ApprovalState.APPROVED:
            # Use custom grant if provided, otherwise generate a valid one
            grant = self._custom_grants.get(
                request.request_id,
                ApprovalGrant(
                    grant_id=f"grant_{uuid.uuid4()}",
                    request_id=request.request_id,
                    tool_name=request.tool_name,
                    arguments=request.arguments,
                    expires_at=request.timestamp + request.ttl
                )
            )

        return ApprovalResult(
            request_id=request.request_id,
            state=state,
            grant=grant
        )
