"""Local file-based implementation of MemoryProvider using JSON.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.memory.base import MemoryEntry, MemoryProvider
from core.memory.errors import MemoryNotFoundError, MemoryPersistenceError

class LocalFileMemoryProvider(MemoryProvider):
    """A simple persistent memory provider that stores entries in a JSON file.
    """

    def __init__(self, storage_path: Path):
        self._storage_path = storage_path
        self._ensure_storage_exists()

    @property
    def name(self) -> str:
        return "local_file"

    def _ensure_storage_exists(self) -> None:
        """Initialize the storage file if it doesn't exist."""
        if not self._storage_path.exists():
            try:
                self._storage_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_data({})
            except Exception as exc:
                raise MemoryPersistenceError(f"Failed to initialize memory storage: {exc}") from exc

    def _read_data(self) -> Mapping[str, Any]:
        """Read the memory store from disk."""
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            raise MemoryPersistenceError(f"Failed to read memory storage: {exc}") from exc

    def _write_data(self, data: Mapping[str, Any]) -> None:
        """Write the memory store to disk atomically."""
        temp_path = self._storage_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self._storage_path)
        except IOError as exc:
            raise MemoryPersistenceError(f"Failed to write memory storage: {exc}") from exc

    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        data = self._read_data()
        data[entry.id] = {
            "id": entry.id,
            "content": entry.content,
            "timestamp": entry.timestamp,
            "metadata": entry.metadata,
        }
        self._write_data(data)

    async def retrieve(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry by ID."""
        data = self._read_data()
        raw_entry = data.get(entry_id)
        if not raw_entry:
            return None

        return MemoryEntry(
            id=raw_entry["id"],
            content=raw_entry["content"],
            timestamp=raw_entry["timestamp"],
            metadata=raw_entry["metadata"],
        )

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        data = self._read_data()
        if entry_id not in data:
            return False

        del data[entry_id]
        self._write_data(data)
        return True

    async def list_all(self) -> Sequence[MemoryEntry]:
        """List all memories."""
        data = self._read_data()
        return [
            MemoryEntry(
                id=val["id"],
                content=val["content"],
                timestamp=val["timestamp"],
                metadata=val["metadata"],
            )
            for val in data.values()
        ]
