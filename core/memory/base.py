"""Base abstractions for Jarvis OS Persistent Memory.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """A single unit of persistent memory."""
    id: str
    content: str
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    metadata: Mapping[str, Any] = field(default_factory=dict)


class MemoryProvider(ABC):
    """Abstract base class for memory persistence providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique identifier for this provider (e.g., 'local_file', 'sqlite')."""
        raise NotImplementedError

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry in the persistence layer."""
        raise NotImplementedError

    @abstractmethod
    async def retrieve(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry by its unique identifier."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry. Returns True if deleted, False if not found."""
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> Sequence[MemoryEntry]:
        """Retrieve all stored memories."""
        raise NotImplementedError
