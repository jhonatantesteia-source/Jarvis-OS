from typing import Any, Mapping

import pytest

from core.tools import Tool, ToolRegistry, ToolResult


class FakeTool(Tool):
    @property
    def name(self) -> str:
        return "fake_tool"

    @property
    def description(self) -> str:
        return "A fake tool used for testing."

    @property
    def input_schema(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(
            success=True,
            content=kwargs.get("value"),
        )


def test_registry_registers_and_gets_tool() -> None:
    registry = ToolRegistry()
    tool = FakeTool()

    registry.register(tool)

    assert "fake_tool" in registry
    assert registry.get("fake_tool") is tool


def test_registry_returns_none_for_unknown_tool() -> None:
    registry = ToolRegistry()

    assert registry.get("unknown") is None


def test_registry_lists_registered_tools() -> None:
    registry = ToolRegistry()
    tool = FakeTool()

    registry.register(tool)

    assert registry.list() == (tool,)


def test_registry_rejects_duplicate_tool_name() -> None:
    registry = ToolRegistry()

    registry.register(FakeTool())

    with pytest.raises(ValueError, match="Tool already registered"):
        registry.register(FakeTool())


@pytest.mark.anyio
async def test_tool_executes_and_returns_result() -> None:
    tool = FakeTool()

    result = await tool.execute(value="Jarvis")

    assert result.success is True
    assert result.content == "Jarvis"
    assert result.error is None