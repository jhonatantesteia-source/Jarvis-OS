import pytest
import httpx
import json
import asyncio

@pytest.mark.ollama
@pytest.mark.asyncio
async def test_ollama_tool_calling():
    url = "http://localhost:11434/api/chat"
    model = "qwen3:1.7b"

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "Get the current system time",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "What time is it?"}
        ],
        "tools": tools,
        "stream": False
    }

    print(f"Sending request to Ollama with model {model}...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        message = data.get("message", {})
        tool_calls = message.get("tool_calls", [])

        assert tool_calls, f"Ollama did not return any tool calls. Response: {data}"
        for tc in tool_calls:
            assert "function" in tc
