# backend/opsagent/tests/test_local_exec_tool.py
import pytest
from opsagent.tools.local_exec import local_exec


@pytest.mark.asyncio
async def test_local_exec_echo():
    result = await local_exec(command="echo hello")
    assert result.success is True
    assert "hello" in result.output


@pytest.mark.asyncio
async def test_local_exec_failing_command():
    result = await local_exec(command="nonexistent_command_xyz")
    assert result.success is False


@pytest.mark.asyncio
async def test_local_exec_tooldef():
    td = local_exec._tooldef
    assert td.name == "local_exec"
    assert td.risk_level.value == "MEDIUM_WRITE"
    assert td.requires_approval is True
    schema = td.to_openai_schema()
    assert schema["function"]["name"] == "local_exec"
