# backend/opsagent/tools/ssh.py
from opsagent.tools.base import tool
from opsagent.core.types import RiskLevel


@tool(
    name="ssh_exec",
    description="Execute a command on a remote host via SSH. Returns stdout, stderr, and exit code.",
    parameters={
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "Hostname or IP address"},
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout_seconds": {"type": "integer", "default": 30, "description": "Command timeout"},
        },
        "required": ["host", "command"],
    },
    risk_level=RiskLevel.READ,
    requires_approval=False,
)
async def ssh_exec(host: str, command: str, timeout_seconds: int = 30, **kwargs):
    """
    Execute a command on a remote host via SSH.

    Risk is READ by default because we can't statically analyze the command.
    The safety engine may re-score based on command content at the call site.
    """
    import asyncio

    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=accept-new",
            host, command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_seconds,
        )
        from opsagent.core.types import ToolResult
        return ToolResult(
            success=proc.returncode == 0,
            output=stdout.decode('utf-8', errors='replace').strip() or "(no output)",
            error=stderr.decode('utf-8', errors='replace').strip() or None,
            metadata={"exit_code": proc.returncode, "host": host},
        )
    except asyncio.TimeoutError:
        from opsagent.core.types import ToolResult
        return ToolResult(success=False, output="", error=f"Command timed out after {timeout_seconds}s")
    except FileNotFoundError:
        from opsagent.core.types import ToolResult
        return ToolResult(success=False, output="", error="ssh client not found. Install openssh-client.")
