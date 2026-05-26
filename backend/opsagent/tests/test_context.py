# backend/opsagent/tests/test_context.py
from opsagent.core.context import ContextManager
from opsagent.core.types import RiskEnv


def test_build_context_defaults():
    cm = ContextManager()
    ctx = cm.build_context(session_id="s1", operator="op")
    assert ctx.session_id == "s1"
    assert ctx.operator == "op"
    assert ctx.env_type == RiskEnv.DEVELOPMENT
    assert ctx.environment_name is None


def test_build_context_prod():
    cm = ContextManager()
    ctx = cm.build_context(
        session_id="s2",
        operator="admin",
        env_name="prod-k8s",
        env_type="production",
        constraints_md="No deploys on Friday",
    )
    assert ctx.env_type == RiskEnv.PRODUCTION
    assert "No deploys on Friday" in ctx.constraints_md


def test_system_prompt_includes_tools():
    cm = ContextManager(global_constraints="Always confirm deletes")
    ctx = cm.build_context(session_id="s1", operator="op")
    prompt = cm.build_system_prompt(ctx, ["ssh_exec", "k8s_get", "db_query"])
    assert "Always confirm deletes" in prompt
    assert "ssh_exec" in prompt
    assert "k8s_get" in prompt


def test_system_prompt_includes_memory():
    cm = ContextManager(memory_entries=[
        {"memory_type": "fault_pattern", "title": "OOM crash", "content": "Check memory limit first"}
    ])
    ctx = cm.build_context(session_id="s1", operator="op")
    prompt = cm.build_system_prompt(ctx, ["ssh_exec"])
    assert "OOM crash" in prompt
    assert "Check memory limit first" in prompt
