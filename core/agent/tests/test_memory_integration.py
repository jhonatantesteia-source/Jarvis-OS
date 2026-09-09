import pytest
import pytest_asyncio
from pathlib import Path
import tempfile
import shutil
from core.agent.runtime import AgentRuntime
from core.agent.models import AgentRequest, AgentResponse
from core.llm.base import LLMProvider
from core.llm.models import LLMRequest, LLMResponse
from core.tools import ToolRegistry
from core.tools.boundary import ToolInvocationBoundary
from core.tools.executor import ToolExecutor
from core.tools.policy import DefaultPolicyEngine
from core.memory.base import MemoryProvider
from core.memory.providers.local_file import LocalFileMemoryProvider

class FakeLLMProvider(LLMProvider):
    def __init__(self, responses):
        self._responses = responses
        self._call_count = 0

    @property
    def name(self) -> str: return "fake"
    @property
    def supports_tools(self) -> bool: return True

    async def complete(self, request, **kwargs):
        res = self._responses[self._call_count] if self._call_count < len(self._responses) else self._responses[-1]
        self._call_count += 1
        return res

    async def health_check(self) -> bool: return True

@pytest.fixture
def memory_setup():
    def _setup(responses):
        tmpdir = tempfile.mkdtemp()
        storage_path = Path(tmpdir) / "mem.json"
        memory_provider = LocalFileMemoryProvider(storage_path)

        registry = ToolRegistry()
        from core.tools.policy import ToolRiskLevel, DefaultPolicyEngine
        risk_map = {
            "store_memory": ToolRiskLevel.LOW,
            "retrieve_memory": ToolRiskLevel.LOW,
            "list_memories": ToolRiskLevel.LOW,
            "delete_memory": ToolRiskLevel.LOW,
        }
        policy = DefaultPolicyEngine(risk_map=risk_map)
        boundary = ToolInvocationBoundary(registry, policy)
        executor = ToolExecutor()
        provider = FakeLLMProvider(responses)

        runtime = AgentRuntime(provider, registry, boundary, executor, memory_provider=memory_provider)

        return runtime, tmpdir
    return _setup

@pytest.mark.anyio
async def test_memory_tool_integration(memory_setup):
    """Verify that the agent can use memory tools to store and then retrieve info."""
    responses = [
        # 1. LLM decides to store memory
        LLMResponse(content="", tool_calls=({"name": "store_memory", "arguments": {"content": "The secret code is 1234"}, "id": "c1"},)),
        # 2. LLM decides to retrieve memory
        LLMResponse(content="", tool_calls=({"name": "retrieve_memory", "arguments": {"entry_id": "mem_id_from_prev"}, "id": "c2"},)),
        # 3. Final answer
        LLMResponse(content="The secret code is 1234"),
    ]
    # Wait, the retrieve_memory tool requires the exact ID.
    # Since store_memory generates a UUID, we can't easily predict it in a FakeLLMProvider script
    # unless we mock the UUID or use a fixed one for the test.
    # Instead, let's test store and retrieve separately.

    runtime, tmpdir = memory_setup(responses)

    # Test store
    request = AgentRequest(messages=[{"role": "user", "content": "Remember that 2+2=4"}])
    # We only want to run one round for this simple check
    runtime._max_tool_rounds = 1
    response = await runtime.run(request)

    # Verify tool was called
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "store_memory"

    # Verify it's actually in the provider
    provider = runtime._memory_provider
    all_mem = await provider.list_all()
    assert len(all_mem) == 1
    assert "The secret code is 1234" in all_mem[0].content

    shutil.rmtree(tmpdir)

@pytest.mark.anyio
async def test_memory_tool_retrieval(memory_setup):
    """Verify that the agent can retrieve a known memory."""
    responses = [
        LLMResponse(content="", tool_calls=({"name": "retrieve_memory", "arguments": {"entry_id": "test_id"}, "id": "c1"},)),
        LLMResponse(content="Found it!"),
    ]

    # Pre-seed the memory
    runtime, tmpdir = memory_setup(responses)
    from core.memory.base import MemoryEntry
    await runtime._memory_provider.store(MemoryEntry(id="test_id", content="Secret info"))

    request = AgentRequest(messages=[{"role": "user", "content": "What is the secret info?"}])
    response = await runtime.run(request)

    assert "Found it!" in response.content
    assert response.tool_calls[0].name == "retrieve_memory"

    shutil.rmtree(tmpdir)
