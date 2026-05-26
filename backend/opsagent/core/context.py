# backend/opsagent/core/context.py
from dataclasses import dataclass, field
from opsagent.core.types import AgentContext, RiskEnv


@dataclass
class ContextManager:
    """Manages the three-layer context (global / environment / session)."""
    global_constraints: str = ""
    memory_entries: list[dict] = field(default_factory=list)

    def build_context(self, env_name: str | None = None, **kwargs) -> AgentContext:
        env_type = kwargs.pop('env_type', RiskEnv.DEVELOPMENT)
        constraints = kwargs.pop('constraints_md', '')
        topology = kwargs.pop('topology_json', {})

        return AgentContext(
            session_id=kwargs.pop('session_id', ''),
            operator=kwargs.pop('operator', 'admin'),
            environment_name=env_name,
            env_type=RiskEnv(env_type) if isinstance(env_type, str) else env_type,
            constraints_md=constraints,
            topology_json=topology,
        )

    def build_system_prompt(self, ctx: AgentContext, available_tools: list[str]) -> str:
        memory_text = "\n".join(
            f"- [{m.get('memory_type', '')}] {m.get('title', '')}: {m.get('content', '')}"
            for m in self.memory_entries
        ) if self.memory_entries else "(none)"

        return f"""You are an IT operations agent. You execute operations tasks using available tools.

## Global Constraints
{self.global_constraints or '(none)'}

## Environment: {ctx.environment_name or 'none'}
Type: {ctx.env_type.value}
Constraints:
{ctx.constraints_md or '(none)'}

## Agent Memory
{memory_text}

## Available Tools
{', '.join(available_tools)}

## Rules
- Read-only tools execute silently. Write tools require confirmation.
- Estimate blast radius before high-risk operations.
- Prefer parallel sub-agent dispatch for independent diagnostics.
- Report findings as structured output (tables when comparing).
"""
