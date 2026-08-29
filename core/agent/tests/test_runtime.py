"""Unit tests for the Agent Runtime.

Everything here is in-process and deterministic: a FakeLLMProvider replaces
any real LLM, and simple Tool stubs replace any real integration. No sleeps,
no HTTP, no external services.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pytest

from core.agent import (
    AgentRequest,
    AgentRuntime,
    InvalidLLMResponseError,
    ToolNotFoundError,
)
from core.llm import LLMProvider
from core.llm.models import LLMRequest, LLMResponse
from core.tools import Tool, ToolRegistry, ToolResult


class FakeLLMProvider(LLMProvider):
    """Deterministic LLM provider stub.

    Returns each scripted response in order. Once only one response
    remains, it keeps returning that same response.
    """

    def __init__(self, responses: Sequence[LLMResponse]) -> None:
        if not responses:
            raise ValueError("FakeLLMProvider requires at least one response")
        self._responses: list[LLMResponse] = list(responses)
        self.calls: list[list[Mapping[str, Any]]] = []
        self.received_tools: list[Sequence[Mapping[str, Any]] | None] = []

    @property
    def supports_tools(self) -> bool:
        return True

    async def complete(
        self,
        request: LLMRequest,
        **kwargs: Any,
    ) -> LLMResponse:
        messages = request.messages
        tools = kwargs.get("tools")
        self.calls.append(list(messages))
        self.received_tools.append(tools)
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]

    async def health_check(self) -> bool:
        return True


class EchoTool(Tool):
    """A trivial tool used to exercise the successful tool-call path."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes back the provided text."

    @property
    def input_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {"text": {"type": "string"}},
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=True, content=kwargs.get("text"))


class FailingTool(Tool):
    """A tool that always reports failure, for the error-path test."""

    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "A tool that always fails."

    @property
    def input_schema(self) -> Mapping[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=False, error="boom")


def _user_request(text: str) -> AgentRequest:
    return AgentRequest(messages=[{"role": "user", "content": text}])


# 1. Tool definitions are exposed to the provider via `tools=`.
@pytest.mark.anyio
async def test_tool_definitions_are_sent_to_provider() -> None:
    provider = FakeLLMProvider([LLMResponse(content="ok")])
    registry = ToolRegistry()
    tool = EchoTool()
    registry.register(tool)

    agent = AgentRuntime(provider, registry)
    await agent.run(_user_request("hi"))

    assert len(provider.received_tools) == 1
    assert provider.received_tools[0] == (
        {
            "name": "echo",
            "description": tool.description,
            "input_schema": tool.input_schema,
        },
    )


# 2. Multiple registered tools are all exposed to the provider.
@pytest.mark.anyio
async def test_multiple_tool_definitions_are_all_sent_to_provider() -> None:
    provider = FakeLLMProvider([LLMResponse(content="ok")])
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(FailingTool())

    agent = AgentRuntime(provider, registry)
    await agent.run(_user_request("hi"))

    tools_sent = provider.received_tools[0]
    assert tools_sent is not None
    assert {definition["name"] for definition in tools_sent} == {
        "echo",
        "failing_tool",
    }
    assert len(tools_sent) == 2


# 3. A tool call is identified and produced in the AgentResponse.
@pytest.mark.anyio
async def test_agent_produces_tool_call_response() -> None:
    tool_call_response = LLMResponse(
        content="Let me check that.",
        tool_calls=({"name": "echo", "arguments": {"text": "ping"}},),
    )
    provider = FakeLLMProvider([tool_call_response])

    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = AgentRuntime(provider, registry)

    response = await agent.run(_user_request("echo ping"))

    assert response.content == "Let me check that."
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "echo"
    assert response.tool_calls[0].arguments == {"text": "ping"}
    # Verify only ONE provider call was made (no automatic loop)
    assert len(provider.calls) == 1


# 4. The history preserves the request in the canonical shape.
@pytest.mark.anyio
async def test_request_history_is_preserved() -> None:
    tool_call_response = LLMResponse(
        content="Checking...",
        tool_calls=({"id": "call_1", "name": "echo", "arguments": {"text": "ping"}},),
    )
    provider = FakeLLMProvider([tool_call_response])

    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = AgentRuntime(provider, registry)

    await agent.run(_user_request("echo ping"))

    # First call only carries the original user message.
    assert provider.calls[0] == [{"role": "user", "content": "echo ping"}]


# 5. Requesting a tool absent from the registry does NOT fail inside AgentRuntime
#    because AgentRuntime only produces the call. Validation happens at the boundary.
@pytest.mark.anyio
async def test_agent_produces_unknown_tool_call() -> None:
    tool_call_response = LLMResponse(
        content="",
        tool_calls=({"name": "does_not_exist", "arguments": {}},),
    )
    provider = FakeLLMProvider([tool_call_response])
    agent = AgentRuntime(provider, ToolRegistry())

    response = await agent.run(_user_request("use a tool that doesn't exist"))
    assert response.tool_calls[0].name == "does_not_exist"


# 6. A tool reporting failure is NOT handled by AgentRuntime during production.
@pytest.mark.anyio
async def test_agent_produces_failing_tool_call() -> None:
    tool_call_response = LLMResponse(
        content="",
        tool_calls=({"name": "failing_tool", "arguments": {}},),
    )
    provider = FakeLLMProvider([tool_call_response])

    registry = ToolRegistry()
    registry.register(FailingTool())
    agent = AgentRuntime(provider, registry)

    response = await agent.run(_user_request("use the failing tool"))
    assert response.tool_calls[0].name == "failing_tool"


# 7. A malformed tool call from the provider fails loudly.
@pytest.mark.anyio
async def test_malformed_tool_call_raises_invalid_llm_response_error() -> None:
    tool_call_response = LLMResponse(content="", tool_calls=({"arguments": {}},))
    provider = FakeLLMProvider([tool_call_response])
    agent = AgentRuntime(provider, ToolRegistry())

    with pytest.raises(InvalidLLMResponseError):
        await agent.run(_user_request("trigger a malformed tool call"))


# 8. A simple response with no tool calls returns immediately.
@pytest.mark.anyio
async def test_agent_returns_final_response_without_tool_call() -> None:
    provider = FakeLLMProvider([LLMResponse(content="Hello, Jarvis.")])
    agent = AgentRuntime(provider, ToolRegistry())

    response = await agent.run(_user_request("Hi"))

    assert response.content == "Hello, Jarvis."
    assert response.tool_calls == ()
    assert response.rounds_used == 0
    assert len(provider.calls) == 1
