"""Agent Runtime for Jarvis OS.

Implements the first, minimal orchestration loop:

    AgentRequest -> LLMProvider -> (tool call?) -> ToolRegistry -> Tool
        -> ToolResult -> back to LLMProvider -> ... -> AgentResponse

The runtime depends only on the existing ``core.llm`` and ``core.tools``
abstractions. It knows nothing about any concrete LLM provider, does not
implement retries/fallback/circuit-breaking, and does not plan ahead — it
only resolves tool calls one round at a time, up to an explicit limit.
"""
from __future__ import annotations

from typing import Any, Mapping, MutableSequence

from core.llm import LLMProvider, LLMResponse
from core.tools import ToolRegistry

from .models import AgentRequest, AgentResponse, ToolCall

MAX_TOOL_ROUNDS = 5


class AgentError(Exception):
    """Base class for all Agent Runtime errors."""


class ToolNotFoundError(AgentError):
    """Raised when the LLM requests a tool that is not in the ToolRegistry."""


class ToolExecutionError(AgentError):
    """Raised when a registered tool fails, either via a failed ToolResult
    or by raising an unexpected exception."""


class InvalidLLMResponseError(AgentError):
    """Raised when the LLM provider returns a tool call that cannot be
    interpreted (missing/invalid name or arguments)."""


class MaxToolRoundsExceededError(AgentError):
    """Raised when the LLM keeps requesting tool calls past the configured
    round limit, to guard against infinite loops."""


class AgentRuntime:
    """Coordinates a single :class:`LLMProvider` and :class:`ToolRegistry`
    through a bounded tool-call loop.

    The Agent never talks to a concrete LLM or tool implementation directly;
    it only relies on the ``LLMProvider`` and ``ToolRegistry`` contracts.
    """

    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        *,
        max_tool_rounds: int = MAX_TOOL_ROUNDS,
    ) -> None:
        self._provider = provider
        self._tool_registry = tool_registry
        self._max_tool_rounds = max_tool_rounds

    async def run(self, request: AgentRequest) -> AgentResponse:
        """Run the agent loop for a single request and return the final response.

        Raises:
            ToolNotFoundError: the LLM requested a tool absent from the registry.
            ToolExecutionError: a tool failed (failed ToolResult or raised).
            InvalidLLMResponseError: the provider returned a malformed tool call.
            MaxToolRoundsExceededError: the loop exceeded ``max_tool_rounds``.
        """
        messages: MutableSequence[Mapping[str, Any]] = list(request.messages)
        executed_tool_calls: list[ToolCall] = []
        round_count = 0

        while True:
            response = await self._provider.complete(messages)
            tool_calls = self._extract_tool_calls(response)

            if not tool_calls:
                return AgentResponse(
                    content=response.content,
                    tool_calls=tuple(executed_tool_calls),
                    rounds_used=round_count,
                )

            round_count += 1
            if round_count > self._max_tool_rounds:
                raise MaxToolRoundsExceededError(
                    f"Exceeded the maximum of {self._max_tool_rounds} tool call "
                    "rounds without a final answer from the LLM provider."
                )

            messages.append({"role": "assistant", "content": response.content})

            for tool_call in tool_calls:
                result_content = await self._execute_tool_call(tool_call)
                executed_tool_calls.append(tool_call)
                messages.append(
                    {
                        "role": "tool",
                        "name": tool_call.name,
                        "content": result_content,
                    }
                )

    async def _execute_tool_call(self, tool_call: ToolCall) -> Any:
        """Locate and execute a single tool call, surfacing failures loudly."""
        tool = self._tool_registry.get(tool_call.name)
        if tool is None:
            raise ToolNotFoundError(f"Tool not found in registry: {tool_call.name!r}")

        try:
            result = await tool.execute(**tool_call.arguments)
        except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
            raise ToolExecutionError(
                f"Tool {tool_call.name!r} raised an exception: {exc}"
            ) from exc

        if not result.success:
            raise ToolExecutionError(
                result.error or f"Tool {tool_call.name!r} reported failure."
            )

        return result.content

    @staticmethod
    def _extract_tool_calls(response: LLMResponse) -> tuple[ToolCall, ...]:
        """Convert the provider's raw ``tool_calls`` mappings into ``ToolCall``s."""
        tool_calls: list[ToolCall] = []

        for raw_call in response.tool_calls:
            if not isinstance(raw_call, Mapping):
                raise InvalidLLMResponseError(
                    f"Malformed tool call from provider: {raw_call!r}"
                )

            name = raw_call.get("name")
            if not isinstance(name, str) or not name:
                raise InvalidLLMResponseError(
                    f"Tool call missing a valid 'name': {raw_call!r}"
                )

            arguments = raw_call.get("arguments", {})
            if not isinstance(arguments, Mapping):
                raise InvalidLLMResponseError(
                    f"Tool call 'arguments' must be a mapping: {raw_call!r}"
                )

            tool_calls.append(ToolCall(name=name, arguments=dict(arguments)))

        return tuple(tool_calls)
