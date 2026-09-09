"""Tools for interacting with the memory subsystem."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.memory.base import MemoryEntry, MemoryProvider
from core.tools.base import Tool, ToolResult

class StoreMemoryTool(Tool):
    """Stores information in persistent memory."""
    def __init__(self, memory_provider: MemoryProvider):
        self._memory_provider = memory_provider

    @property
    def name(self) -> str:
        return "store_memory"

    @property
    def description(self) -> str:
        return "Stores a piece of information in persistent memory for future retrieval."

    @property
    def input_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["content"],
        }

    async def execute(self, content: str, metadata: Mapping[str, Any] = None) -> ToolResult:
        import uuid
        entry_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            metadata=metadata or {},
        )
        await self._memory_provider.store(entry)
        return ToolResult(success=True, content=f"Stored memory with ID: {entry_id}")


class RetrieveMemoryTool(Tool):
    """Retrieves information from persistent memory by ID."""
    def __init__(self, memory_provider: MemoryProvider):
        self._memory_provider = memory_provider

    @property
    def name(self) -> str:
        return "retrieve_memory"

    @property
    def description(self) -> str:
        return "Retrieves a specific memory entry using its unique ID."

    @property
    def input_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"},
            },
            "required": ["entry_id"],
        }

    async def execute(self, entry_id: str) -> ToolResult:
        entry = await self._memory_provider.retrieve(entry_id)
        if not entry:
            return ToolResult(success=False, error=f"Memory entry {entry_id} not found.")

        return ToolResult(success=True, content=f"Memory found: {entry.content} (Metadata: {entry.metadata})")


class ListMemoriesTool(Tool):
    """Lists all stored memories."""
    def __init__(self, memory_provider: MemoryProvider):
        self._memory_provider = memory_provider

    @property
    def name(self) -> str:
        return "list_memories"

    @property
    def description(self) -> str:
        return "Lists all stored memories, including their IDs and content snippets."

    @property
    def input_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs) -> ToolResult:
        memories = await self._memory_provider.list_all()
        if not memories:
            return ToolResult(success=True, content="No memories stored.")

        results = [f"ID: {m.id} | Content: {m.content[:50]}..." for m in memories]
        return ToolResult(success=True, content="\n".join(results))


class DeleteMemoryTool(Tool):
    """Deletes a memory entry."""
    def __init__(self, memory_provider: MemoryProvider):
        self._memory_provider = memory_provider

    @property
    def name(self) -> str:
        return "delete_memory"

    @property
    def description(self) -> str:
        return "Deletes a specific memory entry from persistent storage."

    @property
    def input_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"},
            },
            "required": ["entry_id"],
        }

    async def execute(self, entry_id: str) -> ToolResult:
        deleted = await self._memory_provider.delete(entry_id)
        if not deleted:
            return ToolResult(success=False, error=f"Memory entry {entry_id} not found.")
        return ToolResult(success=True, content=f"Deleted memory {entry_id} successfully.")
