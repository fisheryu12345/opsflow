# backend/opsagent/tools/local_exec.py
from opsagent.tools.base import tool
from opsagent.core.types import RiskLevel


@tool(
    name="local_exec",
    description="Execute a shell command on the local machine. Returns stdout, stderr, and exit code.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute locally"},
            "timeout_seconds": {"type": "integer", "default": 60, "description": "Command timeout"},
            "working_dir": {"type": "string", "description": "Working directory (optional)"},
        },
        "required": ["command"],
    },
    risk_level=RiskLevel.MEDIUM_WRITE,
    requires_approval=True,
)
async def local_exec(command: str, timeout_seconds: int = 60, working_dir: str | None = None, **kwargs):
    import asyncio
    import os

    try:
        proc = await asyncio.create_subprocess_exec(
            "cmd", "/c", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir or os.getcwd(),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_seconds,
        )
        from opsagent.core.types import ToolResult
        return ToolResult(
            success=proc.returncode == 0,
            output=stdout.decode('gbk', errors='replace').strip() or "(no output)",
            error=stderr.decode('gbk', errors='replace').strip() or None,
            metadata={"exit_code": proc.returncode},
        )
    except asyncio.TimeoutError:
        from opsagent.core.types import ToolResult
        return ToolResult(success=False, output="", error=f"Command timed out after {timeout_seconds}s")
