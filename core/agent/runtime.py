"""Agent Runtime for Jarvis OS.

Implements the first, minimal orchestration loop:

    AgentRequest -> LLMProvider -> (tool call?) -> ToolRegistry -> Tool
        -> ToolResult -> back to LLMProvider -> ... -> AgentResponse

The runtime depends only on the existing ``core.llm`` and ``core.tools``
abstractions. It knows nothing about any concrete LLM provider, does not
implement retries/fallback/circuit-breaking, and does not plan ahead — it
only resolves tool calls one round at a time, up to an explicit limit.

Canonical message shapes
-------------------------
The runtime exchanges plain ``Mapping[str, Any]`` messages with the
``LLMProvider`` — the same shape ``LLMProvider.complete`` already accepts.
Beyond the caller-supplied ``{"role": "user", ...}`` messages, the runtime
itself only ever appends two shapes, both provider-agnostic (no OpenAI /
Anthropic / etc. specific fields):

    # the assistant turn that requested one or more tool calls
    {
        "role": "assistant",
        "content": <str>,
        "tool_calls": [{"id": <str>, "name": <str>, "arguments": <dict>}, ...],
    }

    # the result of executing one of those tool calls
    {
        "role": "tool",
        "tool_call_id": <str>,   # correlates back to the entry above
        "name": <str>,
        "content": <Any>,
    }

Translating this canonical shape into a specific vendor's wire format (and
back) is the responsibility of the concrete ``LLMProvider`` implementation,
not the Agent.
"""
from __future__ import annotations

from typing import Any, Mapping, MutableSequence, Sequence

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
        tool_definitions = self._build_tool_definitions()

        while True:
            response = await self._provider.complete(
                messages, tools=tool_definitions or None
            )
            attempt_round = round_count + 1
            tool_calls = self._extract_tool_calls(response, attempt_round)

            if not tool_calls:
                return AgentResponse(
                    content=response.content,
                    tool_calls=tuple(executed_tool_calls),
                    rounds_used=round_count,
                )

            if attempt_round > self._max_tool_rounds:
                raise MaxToolRoundsExceededError(
                    f"Exceeded the maximum of {self._max_tool_rounds} tool call "
                    "rounds without a final answer from the LLM provider."
                )
            round_count = attempt_round

            messages.append(
                self._build_assistant_tool_call_message(response.content, tool_calls)
            )

            for tool_call in tool_calls:
                result_content = await self._execute_tool_call(tool_call)
                executed_tool_calls.append(tool_call)
                messages.append(
                    self._build_tool_result_message(tool_call, result_content)
                )

    def _build_tool_definitions(self) -> tuple[Mapping[str, Any], ...]:
        """Expose every registered tool's (name, description, input_schema)
        to the LLM provider, in a canonical shape independent of any vendor
        wire format. Translating it into a specific provider's function/tool
        schema is that provider's responsibility, not the Agent's."""
        return tuple(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tool_registry.list()
        )

    @staticmethod
    def _build_assistant_tool_call_message(
        content: str, tool_calls: Sequence[ToolCall]
    ) -> Mapping[str, Any]:
        """Canonical representation of an assistant turn that requested one
        or more tool calls, preserved verbatim in the message history."""
        return {
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {"id": tool_call.id, "name": tool_call.name, "arguments": dict(tool_call.arguments)}
                for tool_call in tool_calls
            ],
        }

    @staticmethod
    def _build_tool_result_message(
        tool_call: ToolCall, result_content: Any
    ) -> Mapping[str, Any]:
        """Canonical representation of a tool's result, correlated back to
        the assistant's request via ``tool_call_id``."""
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.name,
            "content": result_content,
        }

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
    def _extract_tool_calls(
        response: LLMResponse, round_number: int
    ) -> tuple[ToolCall, ...]:
        """Convert the provider's raw ``tool_calls`` mappings into ``ToolCall``s.

        ``round_number`` is only used to build a deterministic fallback id
        (``call_<round>_<position>``) for providers that don't supply one,
        so simultaneous tool calls within the same round always correlate
        unambiguously with their results.
        """
        tool_calls: list[ToolCall] = []

        for position, raw_call in enumerate(response.tool_calls, start=1):
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

            call_id = raw_call.get("id", f"call_{round_number}_{position}")
            if not isinstance(call_id, str) or not call_id:
                raise InvalidLLMResponseError(
                    f"Tool call 'id' must be a non-empty string: {raw_call!r}"
                )

            tool_calls.append(ToolCall(name=name, arguments=dict(arguments), id=call_id))

        return tuple(tool_calls)