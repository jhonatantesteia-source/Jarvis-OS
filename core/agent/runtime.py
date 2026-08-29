"""Agent Runtime for Jarvis OS.

Implements the orchestration layer between the user and the LLM provider.
The runtime is responsible for producing an agent response, which may either be
 a final answer or a request for tool invocations.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.agent.errors import AgentError, AgentExecutionError, AgentInputError
from core.agent.interface import Agent
from core.agent.models import AgentContext, AgentRequest, AgentResponse, ToolCall
from core.llm import LLMProvider, LLMRequest, LLMResponse
from core.tools import ToolRegistry

class ToolNotFoundError(AgentError):
    """Raised when the LLM requests a tool that is not in the ToolRegistry."""


class InvalidLLMResponseError(AgentError):
    """Raised when the LLM provider returns a malformed tool call."""


MAX_TOOL_ROUNDS = 5


class DefaultAgent(Agent):
    """A minimal, single-turn agent implementation.

    This agent performs a simple request -> LLM -> response flow without
    executing any tools or actions.
    """

    def __init__(
        self,
        provider: LLMProvider,
        context: AgentContext | None = None,
    ) -> None:
        self._provider = provider
        self._context = context or AgentContext()

    async def run(self, request: AgentRequest) -> AgentResponse:
        """Execute a single turn.

        1. Validate input.
        2. Construct context.
        3. Call LLM provider.
        4. Convert result into AgentResponse.
        """
        if not request.messages:
            raise AgentInputError("AgentRequest must contain at least one message.")

        # Combine context messages with request messages
        messages = list(self._context.messages) + list(request.messages)

        try:
            # Construct LLM request
            llm_request = LLMRequest(
                messages=messages,
            )

            # Call provider
            response = await self._provider.complete(llm_request)

            # Translate to AgentResponse
            return AgentResponse(
                content=response.content,
                model=response.model,
                provider="unknown",
                rounds_used=0,
            )

        except Exception as exc:
            if isinstance(exc, AgentError):
                raise
            raise AgentExecutionError(f"An unexpected error occurred during agent execution: {exc}") from exc


class AgentRuntime(DefaultAgent):
    """Agent runtime that supports tool call production.

    The AgentRuntime identifies when an LLM wants to use tools and produces
    the corresponding ToolCall models, but it does NOT execute them.
    """

    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        context: AgentContext | None = None,
        *,
        max_tool_rounds: int = MAX_TOOL_ROUNDS,
    ) -> None:
        super().__init__(provider, context)
        self._tool_registry = tool_registry
        self._max_tool_rounds = max_tool_rounds

    async def run(self, request: AgentRequest) -> AgentResponse:
        """Produce an agent response, which may contain tool calls.

        Note: This method does NOT execute the tools. Execution is handled
        by the Tool Invocation Boundary and subsequent executor.
        """
        messages = list(self._context.messages) + list(request.messages)
        tool_definitions = self._build_tool_definitions()

        # For a single turn, we just call the provider once.
        # If the provider returns tool calls, we return them as part of the response.
        response = await self._provider.complete(
            LLMRequest(messages=messages),
            tools=tool_definitions or None
        )

        tool_calls = self._extract_tool_calls(response, round_number=1)

        if not tool_calls:
            return AgentResponse(
                content=response.content,
                model=response.model,
                provider="unknown",
                rounds_used=0,
            )

        return AgentResponse(
            content=response.content,
            model=response.model,
            provider="unknown",
            tool_calls=tool_calls,
            rounds_used=1,
        )

    def _build_tool_definitions(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tool_registry.list()
        )

    @staticmethod
    def _extract_tool_calls(
        response: LLMResponse, round_number: int
    ) -> tuple[ToolCall, ...]:
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
