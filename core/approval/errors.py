"""Exceptions raised by the Authorization layer.
"""

from __future__ import annotations

class ApprovalError(Exception):
    """Base exception for all Approval layer failures.
    """

class ApprovalProviderError(ApprovalError):
    """Raised when the ApprovalProvider encounters an internal failure.
    """

class AuthorizationError(ApprovalError):
    """Raised when a grant is invalid, expired, or mismatched.
    """

class ApprovalReplayError(AuthorizationError):
    """Raised when a grant is used more than once.
    """

class ApprovalExpiredError(AuthorizationError):
    """Raised when a grant has passed its expiration time.
    """
