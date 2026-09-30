"""Interface for Jarvis Agents.

This module defines the stable contract for agent execution, ensuring that
the rest of the system remains decoupled from specific agent implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.agent.models import AgentRequest, AgentResponse


@runtime_checkable
class Agent(Protocol):
    """Stable interface for any Jarvis Agent implementation."""

    async def run(
        self,
        request: AgentRequest,
    ) -> AgentResponse:
        """Execute a single agent turn and return the response."""
        ...
