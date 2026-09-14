"""Agent Runtime for Jarvis OS.

Implements the orchestration layer between the user and the LLM provider.
The runtime is responsible for producing an agent response, which may either be
 a final answer or a request for tool invocations.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Mapping, Sequence

from core.agent.errors import AgentError, AgentExecutionError, AgentInputError
from core.agent.interface import Agent
from core.agent.models import AgentContext, AgentRequest, AgentResponse, ToolCall
from core.llm import LLMProvider, LLMRequest, LLMResponse
from core.memory.base import MemoryProvider
from core.approval.base import ApprovalProvider, ApprovalRequest, ApprovalResult, ApprovalState
from core.tools import ToolRegistry
from core.tools.base import ToolResult
from core.tools.boundary import ToolInvocationBoundary
from core.tools.errors import (
    ToolNotFoundError,
    PolicyDeniedError,
    ApprovalRequiredError,
    get_safe_error_message,
)
from core.tools.policy import PolicyDecisionType
from core.tools.audit import SecurityAuditLogger


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
                provider=self._provider.name,
                rounds_used=0,
            )

        except Exception as exc:
            if isinstance(exc, AgentError):
                raise
            raise AgentExecutionError(f"An unexpected error occurred during agent execution: {exc}") from exc


class AgentRuntime(DefaultAgent):
    """Agent runtime that supports tool call production and execution.

    The AgentRuntime orchestrates the loop between the LLM and tool execution:
    LLM -> ToolCall -> InvocationBoundary -> Policy -> Executor -> ToolResult -> LLM.
    """

    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        boundary: ToolInvocationBoundary,
        executor: ToolExecutor,
        context: AgentContext | None = None,
        memory_provider: MemoryProvider | None = None,
        approval_provider: ApprovalProvider | None = None,
        audit_logger: SecurityAuditLogger | None = None,
        *,
        max_tool_rounds: int = MAX_TOOL_ROUNDS,
    ) -> None:
        super().__init__(provider, context)
        self._tool_registry = tool_registry
        self._boundary = boundary
        self._executor = executor
        self._max_tool_rounds = max_tool_rounds
        self._memory_provider = memory_provider
        self._approval_provider = approval_provider
        self._audit_logger = audit_logger

        if self._memory_provider:
            from core.memory.tools import StoreMemoryTool, RetrieveMemoryTool, ListMemoriesTool, DeleteMemoryTool
            self._tool_registry.register(StoreMemoryTool(self._memory_provider))
            self._tool_registry.register(RetrieveMemoryTool(self._memory_provider))
            self._tool_registry.register(ListMemoriesTool(self._memory_provider))
            self._tool_registry.register(DeleteMemoryTool(self._memory_provider))

    async def run(self, request: AgentRequest) -> AgentResponse:
        """Produce an agent response by iterating through tool calls.

        The runtime calls the LLM, executes any requested tools, and feeds the
        results back to the LLM until a final answer is reached or the round
        limit is hit.
        """
        messages = list(self._context.messages) + list(request.messages)
        tool_definitions = self._build_tool_definitions()

        all_executed_calls: list[ToolCall] = []
        current_round = 0

        while current_round < self._max_tool_rounds:
            # 1. Call the provider
            try:
                response = await self._provider.complete(
                    LLMRequest(messages=messages),
                    tools=tool_definitions or None
                )
            except Exception as exc:
                if isinstance(exc, AgentError):
                    raise
                raise AgentExecutionError(f"LLM provider failure: {exc}") from exc

            # 2. Extract tool calls
            tool_calls = self._extract_tool_calls(response, round_number=current_round + 1)

            if not tool_calls:
                return AgentResponse(
                    content=response.content,
                    model=response.model,
                    provider=self._provider.name,
                    tool_calls=tuple(all_executed_calls),
                    rounds_used=current_round,
                )

            # 3. Execute tools
            # Add assistant's tool-call request to history
            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments}}
                    for tc in tool_calls
                ]
            })

            for tool_call in tool_calls:
                all_executed_calls.append(tool_call)

                try:
                    # Validation & Policy
                    validated_call = await self._boundary.validate(tool_call)

                    # Handle Human-in-the-Loop Authorization
                    if validated_call.decision.decision == PolicyDecisionType.REQUIRE_USER_APPROVAL:
                        if not self._approval_provider:
                            result = ToolResult(success=False, error="Approval required but no ApprovalProvider configured.")
                        else:
                            # Create the bound ApprovalRequest
                            approval_request = ApprovalRequest(
                                request_id=tool_call.internal_id or f"req_{time.time()}",
                                tool_name=validated_call.tool.name,
                                arguments=validated_call.call.arguments,
                                risk_level=validated_call.decision.risk_level,
                                reason=validated_call.decision.reason,
                                timestamp=time.time(),
                            )

                            if self._audit_logger:
                                self._audit_logger.log_event(
                                    SecurityAuditLogger.APPROVAL_REQUESTED,
                                    tool_call.internal_id,
                                    validated_call.tool.name,
                                    "PENDING",
                                    validated_call.decision.reason,
                                    risk_level=validated_call.decision.risk_level,
                                )

                            # Async wait for human decision
                            approval_result = await self._approval_provider.request_approval(approval_request)

                            if approval_result.state == ApprovalState.APPROVED and approval_result.grant:
                                # Bind ApprovalResult.request_id to the current request
                                if approval_result.request_id != approval_request.request_id:
                                    result = ToolResult(
                                        success=False,
                                        error=f"Approval result identity mismatch: expected {approval_request.request_id}, got {approval_result.request_id}"
                                    )
                                else:
                                    if self._audit_logger:
                                        self._audit_logger.log_event(
                                            SecurityAuditLogger.APPROVAL_APPROVED,
                                            tool_call.internal_id,
                                            validated_call.tool.name,
                                            "APPROVED",
                                            "User granted approval",
                                        )
                                    # Pass the explicit Grant to the executor
                                    result = await self._executor.execute(validated_call, grant=approval_result.grant)
                            else:
                                if self._audit_logger:
                                    self._audit_logger.log_event(
                                        SecurityAuditLogger.APPROVAL_DENIED,
                                        tool_call.internal_id,
                                        validated_call.tool.name,
                                        "DENIED",
                                        f"User or system denied: {approval_result.state.name}",
                                    )
                                result = ToolResult(
                                    success=False,
                                    error=f"Tool execution denied by user or system: {approval_result.state.name}"
                                )
                    else:
                        # Normal ALLOW flow (or DENY which is handled by executor)
                        result = await self._executor.execute(validated_call)

                except (PolicyDeniedError, ToolNotFoundError) as exc:
                    result = ToolResult(success=False, error=str(exc))
                except Exception as exc:
                    result = ToolResult(success=False, error=get_safe_error_message(exc))

                # Append result to history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result.content if result.success else result.error),
                })

            current_round += 1

        # Max rounds reached
        return AgentResponse(
            content=f"Max tool rounds ({self._max_tool_rounds}) reached. Last response: {response.content}",
            model=response.model,
            provider=self._provider.name,
            tool_calls=tuple(all_executed_calls),
            rounds_used=current_round,
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

            tool_calls.append(ToolCall(
                name=name,
                arguments=dict(arguments),
                id=call_id,
                internal_id=uuid.uuid4().hex,
            ))

        return tuple(tool_calls)
