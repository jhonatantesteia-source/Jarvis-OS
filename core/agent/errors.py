"""Exceptions raised by the Agent Runtime."""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for all Agent Runtime failures."""


class AgentInputError(AgentError):
    """Raised when the agent request is invalid or malformed."""


class AgentExecutionError(AgentError):
    """Raised when an error occurs during agent execution."""
