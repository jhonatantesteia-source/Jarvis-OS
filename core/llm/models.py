"""Domain models for LLM requests and responses.

These models provide a vendor-neutral way to represent the data flowing
through the LLM runtime layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Normalized request sent to an LLM provider."""

    messages: Sequence[Mapping[str, str]]
    model: str | None = None
    system_instruction: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Normalized response returned by an LLM provider."""

    content: str
    model: str | None = None
    tool_calls: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    usage: Mapping[str, int] = field(default_factory=dict)
    raw: Any = None
