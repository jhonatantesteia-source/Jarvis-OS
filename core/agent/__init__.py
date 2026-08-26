"""Agent Runtime abstractions for Jarvis OS.

Wires an ``LLMProvider`` and a ``ToolRegistry`` into a single bounded
tool-call loop:

    Agent
        v
    LLMProvider
        v
    ToolRegistry
        v
    Tool

No concrete LLM provider, memory backend, or frontend integration lives
here — see ``core.llm`` and ``core.tools`` for the underlying contracts
this module builds on.
"""

from .models import AgentRequest, AgentResponse, ToolCall
from .runtime import (
    MAX_TOOL_ROUNDS,
    AgentError,
    AgentRuntime,
    InvalidLLMResponseError,
    MaxToolRoundsExceededError,
    ToolExecutionError,
    ToolNotFoundError,
)

__all__ = [
    "AgentRequest",
    "AgentResponse",
    "ToolCall",
    "AgentRuntime",
    "AgentError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "InvalidLLMResponseError",
    "MaxToolRoundsExceededError",
    "MAX_TOOL_ROUNDS",
]
