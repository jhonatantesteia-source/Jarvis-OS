"""Exceptions raised by the Tool layer.
"""

from __future__ import annotations


class ToolError(Exception):
    """Base exception for all Tool layer failures.
    """


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found in the registry.
    """


class ToolValidationError(ToolError):
    """Raised when a tool call fails validation.
    """


class PolicyDeniedError(ToolError):
    """Raised when a tool call is explicitly denied by the policy engine.
    """


class ApprovalRequiredError(ToolError):
    """Raised when a tool call requires user approval but none was provided.
    """
