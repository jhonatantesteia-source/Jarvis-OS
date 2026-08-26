"""Data contracts for the Jarvis Agent Runtime.

These models define the boundary between :class:`~core.agent.runtime.AgentRuntime`
and its callers. They intentionally know nothing about any concrete LLM
provider or tool implementation — only about the shapes exchanged with
``core.llm`` and ``core.tools``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A single tool invocation requested by an LLM provider.

    Kept as an explicit model — rather than a raw ``Mapping[str, Any]`` —
    so the runtime and its tests have a single, typed shape to work with.

    ``id`` correlates this call with its eventual tool-result message. It is
    taken from the provider's response when present (mirroring how real
    tool-calling APIs identify a call); otherwise the runtime assigns a
    deterministic fallback so multiple simultaneous tool calls in the same
    round never fail to correlate correctly.
    """

    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    id: str | None = None


@dataclass(frozen=True, slots=True)
class AgentRequest:
    """Input to the Agent Runtime: the conversation so far."""

    messages: Sequence[Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class AgentResponse:
    """Final output of the Agent Runtime, after any tool rounds.

    ``tool_calls`` records every tool call executed while producing this
    response (useful for logging/debugging); ``rounds_used`` is the number
    of tool-call rounds that were needed before a final answer was reached.
    """

    content: str
    tool_calls: Sequence[ToolCall] = field(default_factory=tuple)
    rounds_used: int = 0