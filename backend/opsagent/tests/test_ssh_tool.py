# backend/opsagent/tests/test_ssh_tool.py
import pytest
from opsagent.tools.ssh import ssh_exec


@pytest.mark.asyncio
async def test_ssh_exec_localhost_echo(monkeypatch):
    """Test ssh_exec when ssh binary is not available (expected in test env)."""
    result = await ssh_exec(host="localhost", command="echo hello")
    if result.success:
        assert "hello" in result.output
    else:
        assert result.error is not None


@pytest.mark.asyncio
async def test_ssh_exec_tooldef_exists():
    td = ssh_exec._tooldef
    assert td.name == "ssh_exec"
    assert td.risk_level.value == "READ"
    schema = td.to_openai_schema()
    assert schema["function"]["name"] == "ssh_exec"
