"""Ollama provider implementation for Jarvis OS.

This module implements the LLMProvider interface for the Ollama local LLM runtime.
"""

from __future__ import annotations

import httpx
from typing import Any, Mapping

from core.config.settings import settings
from core.llm.base import LLMProvider
from core.llm.models import LLMRequest, LLMResponse


class OllamaProvider(LLMProvider):
    """Provider for the Ollama local LLM runtime."""

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        self._model = model or settings.llm_model or "llama3"
        self._host = host or settings.ollama_host
        self._client = httpx.AsyncClient(base_url=f"{self._host}/api", timeout=120.0)

    @property
    def supports_tools(self) -> bool:
        """Ollama supports tool calling in recent versions."""
        return True

    async def complete(
        self,
        request: LLMRequest,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response using the Ollama /api/chat endpoint."""

        # 1. Prepare payload
        payload = {
            "model": self._model,
            "messages": request.messages,
            "stream": False,
            "options": {
                "temperature": request.temperature if request.temperature is not None else 0.7,
                "num_predict": request.max_tokens if request.max_tokens is not None else 512,
            }
        }

        # 2. Handle tool definitions if provided in kwargs
        tools = kwargs.get("tools")
        if tools:
            # Translate Jarvis tool definitions to Ollama format
            ollama_tools = []
            for tool_def in tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_def["name"],
                        "description": tool_def["description"],
                        "parameters": tool_def["input_schema"],
                    }
                })
            payload["tools"] = ollama_tools

        # 3. Request execution
        try:
            response = await self._client.post("/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            # We wrap this in a generic error or let it bubble up
            # For now, let's raise a RuntimeError to be caught by AgentRuntime
            raise RuntimeError(f"Ollama API error: {exc}") from exc

        # 4. Translate Ollama response to LLMResponse
        message = data.get("message", {})
        content = message.get("content", "")

        # Translate tool calls
        tool_calls = []
        raw_tool_calls = message.get("tool_calls", [])
        for i, tc in enumerate(raw_tool_calls):
            func = tc.get("function", {})
            tool_calls.append({
                "name": func.get("name"),
                "arguments": func.get("arguments", {}),
                "id": f"ollama_{i}" # Ollama doesn't always provide unique IDs per call
            })

        return LLMResponse(
            content=content,
            model=self._model,
            tool_calls=tuple(tool_calls),
            usage=data.get("usage", {}),
            raw=data
        )

    async def health_check(self) -> bool:
        """Check Ollama health by querying available tags."""
        try:
            response = await self._client.get("/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        """Ensure the HTTP client is closed."""
        await self._client.aclose()
