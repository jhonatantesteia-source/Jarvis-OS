"""Exceptions raised by the Memory layer.
"""

from __future__ import annotations


class MemoryError(Exception):
    """Base exception for all Memory layer failures.
    """


class MemoryNotFoundError(MemoryError):
    """Raised when a requested memory entry is not found.
    """


class MemoryPersistenceError(MemoryError):
    """Raised when there is a failure in the persistence backend.
    """


class MemoryValidationError(MemoryError):
    """Raised when a memory entry is malformed or invalid.
    """
