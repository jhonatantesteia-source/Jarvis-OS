import pytest
import pytest_asyncio
from pathlib import Path
import tempfile
import shutil
from core.memory.base import MemoryEntry
from core.memory.providers.local_file import LocalFileMemoryProvider
from core.memory.errors import MemoryPersistenceError

@pytest.fixture
def temp_storage():
    """Creates a temporary directory and returns the path to a memory file."""
    tmpdir = tempfile.mkdtemp()
    storage_path = Path(tmpdir) / "memory.json"
    yield storage_path
    shutil.rmtree(tmpdir)

@pytest.mark.anyio
async def test_store_and_retrieve(temp_storage):
    """Test basic storage and retrieval of a memory entry."""
    provider = LocalFileMemoryProvider(temp_storage)
    entry = MemoryEntry(id="mem1", content="Hello World", metadata={"tag": "test"})

    await provider.store(entry)
    retrieved = await provider.retrieve("mem1")

    assert retrieved is not None
    assert retrieved.id == "mem1"
    assert retrieved.content == "Hello World"
    assert retrieved.metadata == {"tag": "test"}
    assert retrieved.timestamp > 0

@pytest.mark.anyio
async def test_retrieve_missing(temp_storage):
    """Test retrieval of a non-existent memory."""
    provider = LocalFileMemoryProvider(temp_storage)
    retrieved = await provider.retrieve("unknown")
    assert retrieved is None

@pytest.mark.anyio
async def test_delete_existing(temp_storage):
    """Test deleting an existing memory."""
    provider = LocalFileMemoryProvider(temp_storage)
    entry = MemoryEntry(id="mem1", content="Delete me")
    await provider.store(entry)

    deleted = await provider.delete("mem1")
    assert deleted is True

    retrieved = await provider.retrieve("mem1")
    assert retrieved is None

@pytest.mark.anyio
async def test_delete_missing(temp_storage):
    """Test deleting a non-existent memory."""
    provider = LocalFileMemoryProvider(temp_storage)
    deleted = await provider.delete("unknown")
    assert deleted is False

@pytest.mark.anyio
async def test_list_all(temp_storage):
    """Test listing all stored memories."""
    provider = LocalFileMemoryProvider(temp_storage)
    entries = [
        MemoryEntry(id="m1", content="C1"),
        MemoryEntry(id="m2", content="C2"),
        MemoryEntry(id="m3", content="C3"),
    ]
    for e in entries:
        await provider.store(e)

    all_memories = await provider.list_all()
    assert len(all_memories) == 3
    ids = {m.id for m in all_memories}
    assert ids == {"m1", "m2", "m3"}

@pytest.mark.anyio
async def test_persistence_across_restarts(temp_storage):
    """Test that memories survive provider recreation."""
    # 1. First provider stores data
    provider1 = LocalFileMemoryProvider(temp_storage)
    entry = MemoryEntry(id="persistent1", content="I survive")
    await provider1.store(entry)

    # 2. Second provider (new instance, same file) retrieves data
    provider2 = LocalFileMemoryProvider(temp_storage)
    retrieved = await provider2.retrieve("persistent1")

    assert retrieved is not None
    assert retrieved.content == "I survive"

@pytest.mark.anyio
async def test_metadata_persistence(temp_storage):
    """Test that complex metadata survives persistence."""
    provider = LocalFileMemoryProvider(temp_storage)
    metadata = {
        "category": "personal",
        "priority": 1,
        "tags": ["work", "urgent"],
        "nested": {"key": "value"}
    }
    entry = MemoryEntry(id="meta1", content="Content", metadata=metadata)
    await provider.store(entry)

    retrieved = await provider.retrieve("meta1")
    assert retrieved.metadata == metadata

@pytest.mark.anyio
async def test_corrupt_storage_behavior(temp_storage):
    """Test that corrupt JSON causes MemoryPersistenceError."""
    # Write invalid JSON to the file
    temp_storage.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_storage, "w", encoding="utf-8") as f:
        f.write("this is not json {")

    provider = LocalFileMemoryProvider(temp_storage)
    with pytest.raises(MemoryPersistenceError):
        await provider.retrieve("any")
