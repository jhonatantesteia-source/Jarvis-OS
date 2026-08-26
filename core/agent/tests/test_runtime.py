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
    ToolCall,
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
    """

    def __init__(self, responses: Sequence[LLMResponse]) -> None:
        if not responses:
            raise ValueError("FakeLLMProvider requires at least one response")
        self._responses: list[LLMResponse] = list(responses)
        self.calls: list[list[Mapping[str, Any]]] = []

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


@pytest.mark.anyio
async def test_agent_returns_final_response_without_tool_call() -> None:
    provider = FakeLLMProvider([LLMResponse(content="Hello, Jarvis.")])
    agent = AgentRuntime(provider, ToolRegistry())

    response = await agent.run(_user_request("Hi"))

    assert response.content == "Hello, Jarvis."
    assert response.tool_calls == ()
    assert response.rounds_used == 0
    assert len(provider.calls) == 1


@pytest.mark.anyio
async def test_agent_executes_tool_call_and_returns_final_response() -> None:
    tool_call_response = LLMResponse(
        content="",
        tool_calls=({"name": "echo", "arguments": {"text": "ping"}},),
    )
    final_response = LLMResponse(content="Tool said: ping")
    provider = FakeLLMProvider([tool_call_response, final_response])

    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = AgentRuntime(provider, registry)

    response = await agent.run(_user_request("echo ping"))

    # Final response reflects the round after the tool executed.
    assert response.content == "Tool said: ping"
    assert response.rounds_used == 1
    assert response.tool_calls == (ToolCall(name="echo", arguments={"text": "ping"}),)

    # The provider must have been called once to request the tool call and
    # once more with the tool's result folded back into the conversation.
    assert len(provider.calls) == 2
    second_call_messages = provider.calls[1]
    assert any(
        message.get("role") == "tool" and message.get("content") == "ping"
        for message in second_call_messages
    )


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


@pytest.mark.anyio
async def test_malformed_tool_call_raises_invalid_llm_response_error() -> None:
    tool_call_response = LLMResponse(content="", tool_calls=({"arguments": {}},))
    provider = FakeLLMProvider([tool_call_response])
    agent = AgentRuntime(provider, ToolRegistry())

    with pytest.raises(InvalidLLMResponseError):
        await agent.run(_user_request("trigger a malformed tool call"))


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
