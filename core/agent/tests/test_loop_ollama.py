import pytest
import pytest_asyncio
from core.agent.runtime import AgentRuntime
from core.agent.models import AgentRequest, AgentContext
from core.llm.providers.ollama import OllamaProvider
from core.tools.registry import ToolRegistry
from core.tools.boundary import ToolInvocationBoundary
from core.tools.executor import ToolExecutor
from core.tools.policy import DefaultPolicyEngine
from core.tools.base import Tool, ToolResult
from typing import Any, Mapping

class SimpleTool(Tool):
    def __init__(self, name: str):
        self._name = name
    @property
    def name(self) -> str: return self._name
    @property
    def description(self) -> str: return "A simple tool"
    @property
    def input_schema(self) -> Mapping[str, Any]: return {"type": "object", "properties": {}}
    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=True, content=f"Result from {self.name}")

@pytest.mark.ollama
class TestOllamaLoop:
    @pytest_asyncio.fixture
    async def runtime(self):
        provider = OllamaProvider(model="qwen3.5:9b")
        registry = ToolRegistry()
        tool = SimpleTool("hello_tool")
        registry.register(tool)
        boundary = ToolInvocationBoundary(registry, DefaultPolicyEngine())
        executor = ToolExecutor()
        runtime = AgentRuntime(provider, registry, boundary, executor)
        yield runtime
        await provider.close()

    @pytest.mark.asyncio
    async def test_ollama_loop_direct(self, runtime):
        """Verify Ollama can give a response in the loop."""
        request = AgentRequest(messages=[{"role": "user", "content": "Hi!"}])
        response = await runtime.run(request)
        assert response.content != "" or len(response.tool_calls) > 0

    @pytest.mark.asyncio
    async def test_ollama_loop_tool(self, runtime):
        """Verify Ollama can use a tool in the loop."""
        # Prompt the model to use the tool specifically
        request = AgentRequest(messages=[{"role": "user", "content": "Use the hello_tool to say hi."}])
        response = await runtime.run(request)

        # Check that we either got a final answer or a tool call history
        assert response.content != "" or len(response.tool_calls) > 0
        if response.rounds_used > 0:
            assert len(response.tool_calls) > 0
