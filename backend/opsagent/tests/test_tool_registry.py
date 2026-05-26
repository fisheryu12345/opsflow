# backend/opsagent/tests/test_tool_registry.py
import pytest
from opsagent.core.tool_registry import register, get, list_all, clear
from opsagent.tools.base import ToolDef, tool
from opsagent.core.types import RiskLevel


async def _noop(**kwargs):
    from opsagent.core.types import ToolResult
    return ToolResult(success=True, output="ok")


def test_register_and_get():
    clear()
    td = ToolDef(name="test.tool", description="A test", parameters={},
                 risk_level=RiskLevel.READ, handler=_noop)
    register(td)
    assert get("test.tool") is td
    assert len(list_all()) == 1


def test_duplicate_is_idempotent():
    clear()
    td = ToolDef(name="dup.tool", description="Dup", parameters={},
                 risk_level=RiskLevel.READ, handler=_noop)
    register(td)
    register(td)  # Should not raise — idempotent
    assert len(list_all()) == 1  # Still only one registration


def test_tool_decorator():
    clear()

    @tool(name="deco.tool", description="Decorated", parameters={
        "type": "object", "properties": {}, "required": []
    }, risk_level=RiskLevel.LOW_WRITE)
    async def my_tool(**kwargs):
        from opsagent.core.types import ToolResult
        return ToolResult(success=True, output="done")

    register(my_tool._tooldef)
    got = get("deco.tool")
    assert got is not None
    assert got.risk_level == RiskLevel.LOW_WRITE
    assert "deco.tool" in got.to_openai_schema()["function"]["name"]
