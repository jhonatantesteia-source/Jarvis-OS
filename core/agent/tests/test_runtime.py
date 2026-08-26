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
    MaxToolRoundsExceededError,
    ToolExecutionError,
    ToolNotFoundError,
)
from core.llm import LLMProvider, LLMResponse
from core.tools import Tool, ToolRegistry, ToolResult


class FakeLLMProvider(LLMProvider):
    """Deterministic LLM provider stub.

    Returns each scripted response in order. Once only one response
    remains, it keeps returning that same response — this lets a single
    scripted response stand in for "the LLM keeps asking for the same tool
    call forever", which is what the round-limit test needs.

    Every call's ``messages`` and ``tools`` are recorded so tests can assert
    on exactly what the Agent sent the provider.
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
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
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


# 3. A tool call is identified, resolved, executed, and its result flows
#    back into the LLM, producing a final response.
@pytest.mark.anyio
async def test_agent_executes_tool_call_and_returns_final_response() -> None:
    tool_call_response = LLMResponse(
        content="Let me check that.",
        tool_calls=({"name": "echo", "arguments": {"text": "ping"}},),
    )
    final_response = LLMResponse(content="Tool said: ping")
    provider = FakeLLMProvider([tool_call_response, final_response])

    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = AgentRuntime(provider, registry)

    response = await agent.run(_user_request("echo ping"))

    assert response.content == "Tool said: ping"
    assert response.rounds_used == 1
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "echo"
    assert response.tool_calls[0].arguments == {"text": "ping"}
    assert len(provider.calls) == 2


# 3b. Multiple tool calls requested in a single round are all executed and
#     their results all flow back to the LLM.
@pytest.mark.anyio
async def test_agent_executes_multiple_tool_calls_in_a_single_round() -> None:
    tool_call_response = LLMResponse(
        content="",
        tool_calls=(
            {"id": "call_a", "name": "echo", "arguments": {"text": "one"}},
            {"id": "call_b", "name": "echo", "arguments": {"text": "two"}},
        ),
    )
    final_response = LLMResponse(content="done")
    provider = FakeLLMProvider([tool_call_response, final_response])

    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = AgentRuntime(provider, registry)

    response = await agent.run(_user_request("do two things"))

    assert response.content == "done"
    assert response.rounds_used == 1
    assert [tc.name for tc in response.tool_calls] == ["echo", "echo"]

    second_call_messages = provider.calls[1]
    tool_result_messages = [m for m in second_call_messages if m.get("role") == "tool"]
    assert {m["content"] for m in tool_result_messages} == {"one", "two"}
    assert {m["tool_call_id"] for m in tool_result_messages} == {"call_a", "call_b"}


# 4. The history preserves both the assistant's tool-call request and the
#    tool's result, in the canonical (provider-agnostic) shape.
@pytest.mark.anyio
async def test_tool_call_history_is_preserved_in_canonical_format() -> None:
    tool_call_response = LLMResponse(
        content="Let me check that.",
        tool_calls=({"id": "call_1", "name": "echo", "arguments": {"text": "ping"}},),
    )
    final_response = LLMResponse(content="Tool said: ping")
    provider = FakeLLMProvider([tool_call_response, final_response])

    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = AgentRuntime(provider, registry)

    await agent.run(_user_request("echo ping"))

    # First call only carries the original user message.
    assert provider.calls[0] == [{"role": "user", "content": "echo ping"}]

    # Second call must additionally carry the assistant's tool-call request
    # (content + structured tool_calls) and the tool's result, correlated by
    # tool_call_id — never just the bare final content.
    second_call_messages = provider.calls[1]
    assert second_call_messages[0] == {"role": "user", "content": "echo ping"}

    assistant_message = second_call_messages[1]
    assert assistant_message == {
        "role": "assistant",
        "content": "Let me check that.",
        "tool_calls": [{"id": "call_1", "name": "echo", "arguments": {"text": "ping"}}],
    }

    tool_message = second_call_messages[2]
    assert tool_message == {
        "role": "tool",
        "tool_call_id": "call_1",
        "name": "echo",
        "content": "ping",
    }


# 5. Requesting a tool absent from the registry fails loudly.
@pytest.mark.anyio
async def test_unknown_tool_raises_tool_not_found_error() -> None:
    tool_call_response = LLMResponse(
        content="",
        tool_calls=({"name": "does_not_exist", "arguments": {}},),
    )
    provider = FakeLLMProvider([tool_call_response])
    agent = AgentRuntime(provider, ToolRegistry())

    with pytest.raises(ToolNotFoundError, match="does_not_exist"):
        await agent.run(_user_request("use a tool that doesn't exist"))


# 6. A tool reporting failure fails loudly.
@pytest.mark.anyio
async def test_failing_tool_raises_tool_execution_error() -> None:
    tool_call_response = LLMResponse(
        content="",
        tool_calls=({"name": "failing_tool", "arguments": {}},),
    )
    provider = FakeLLMProvider([tool_call_response])

    registry = ToolRegistry()
    registry.register(FailingTool())
    agent = AgentRuntime(provider, registry)

    with pytest.raises(ToolExecutionError, match="boom"):
        await agent.run(_user_request("use the failing tool"))


# 7. A malformed tool call from the provider fails loudly.
@pytest.mark.anyio
async def test_malformed_tool_call_raises_invalid_llm_response_error() -> None:
    tool_call_response = LLMResponse(content="", tool_calls=({"arguments": {}},))
    provider = FakeLLMProvider([tool_call_response])
    agent = AgentRuntime(provider, ToolRegistry())

    with pytest.raises(InvalidLLMResponseError):
        await agent.run(_user_request("trigger a malformed tool call"))


# 7b. A simple response with no tool calls returns immediately.
@pytest.mark.anyio
async def test_agent_returns_final_response_without_tool_call() -> None:
    provider = FakeLLMProvider([LLMResponse(content="Hello, Jarvis.")])
    agent = AgentRuntime(provider, ToolRegistry())

    response = await agent.run(_user_request("Hi"))

    assert response.content == "Hello, Jarvis."
    assert response.tool_calls == ()
    assert response.rounds_used == 0
    assert len(provider.calls) == 1


# 8. The round limit stops an LLM that never stops requesting tool calls.
@pytest.mark.anyio
async def test_tool_round_limit_prevents_infinite_loop() -> None:
    # A single scripted response that the FakeLLMProvider will keep
    # returning forever, simulating an LLM that never stops calling tools.
    tool_call_response = LLMResponse(
        content="",
        tool_calls=({"name": "echo", "arguments": {"text": "again"}},),
    )
    provider = FakeLLMProvider([tool_call_response])

    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = AgentRuntime(provider, registry, max_tool_rounds=2)

    with pytest.raises(MaxToolRoundsExceededError):
        await agent.run(_user_request("loop forever"))

    # 2 rounds executed (2 provider calls), plus 1 more call that revealed
    # the LLM was still asking for a tool call beyond the allowed limit.
    assert len(provider.calls) == 3