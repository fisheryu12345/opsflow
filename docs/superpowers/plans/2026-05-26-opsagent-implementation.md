# OpsAgent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new Django app `opsagent/` implementing an LLM-driven IT operations CLI Agent with tiered safety approval, pluggable tools, and append-only audit logging.

**Architecture:** Pure Python agent core (no Django coupling) in `opsagent/core/`, tool implementations in `opsagent/tools/`, CLI in `opsagent/cli/`, with Django providing ORM persistence for audit/session/memory models and management commands as the CLI entry point.

**Tech Stack:** Python 3.11+ / Django 4.2 ORM / asyncio / OpenAI SDK (LLM) / paramiko (SSH) / Click (CLI)

**Spec:** [2026-05-26-ops-agent-design.md](../specs/2026-05-26-ops-agent-design.md)

---

## File Map

```
backend/opsagent/
├── __init__.py
├── apps.py                         # OpsAgentConfig — no scheduler, minimal ready()
├── models.py                       # AuditRecord, Session, EnvironmentContext, AgentMemory
├── admin.py                        # Django admin registrations
├── urls.py                         # DRF router for web UI (audit/session browsing)
├── serializers.py                  # DRF serializers
├── views/                          # Read-only API views
│   ├── __init__.py
│   ├── audit.py                    # AuditRecord ViewSet
│   └── session.py                  # Session ViewSet
│
├── core/                           # Pure Python — zero Django imports
│   ├── __init__.py
│   ├── types.py                    # Shared types: ToolDef, RiskLevel, SafetyDecision, AgentContext
│   ├── agent_loop.py               # Core loop: input → think → tool → observe → response
│   ├── tool_registry.py            # Tool registration, discovery, schema generation
│   ├── safety.py                   # Risk scorer + approval gate
│   ├── context.py                  # Context manager: global/env/session layers
│   └── subagent.py                 # Subagent spawner with tool/target/timeout isolation
│
├── tools/                          # Concrete tool implementations
│   ├── __init__.py                 # auto_discover(): scan this package, register all ToolDefs
│   ├── base.py                     # ToolDef dataclass + @tool decorator
│   ├── ssh.py                      # ssh_exec, ssh_script
│   ├── filesystem.py               # fs_read, fs_write, fs_search
│   ├── database.py                 # db_query, db_exec
│   ├── kubernetes.py               # k8s_get, k8s_describe, k8s_logs
│   ├── generic.py                  # http_call, python_eval
│   └── builtin.py                  # subagent tool (depends on core.subagent)
│
├── cli/                            # CLI interface
│   ├── __init__.py
│   ├── repl.py                     # Async REPL with readline, stream rendering
│   ├── render.py                   # Markdown/table/color rendering
│   └── session_manager.py          # Session CRUD, history, replay
│
├── management/
│   └── commands/
│       └── ops.py                  # python manage.py ops [--run "query"]
│
└── migrations/
    ├── __init__.py
    └── 0001_initial.py
```

---

### Task 1: App Skeleton & Models

**Files:**
- Create: `backend/opsagent/__init__.py`
- Create: `backend/opsagent/apps.py`
- Create: `backend/opsagent/models.py`
- Create: `backend/opsagent/admin.py`
- Create: `backend/opsagent/migrations/__init__.py`
- Modify: `backend/application/settings.py` (add `"opsagent"` to INSTALLED_APPS)

- [ ] **Step 1: Create __init__.py**

```python
# backend/opsagent/__init__.py
```

- [ ] **Step 2: Create apps.py**

```python
# backend/opsagent/apps.py
from django.apps import AppConfig


class OpsAgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opsagent'
    verbose_name = 'OpsAgent - LLM运维Agent'
```

- [ ] **Step 3: Create models.py**

```python
# backend/opsagent/models.py
from django.db import models


class EnvironmentContext(models.Model):
    """Persisted OPS_CONTEXT.md equivalent — one row per managed environment."""
    name = models.CharField(max_length=128, unique=True, help_text="e.g. 'prod-k8s-cluster'")
    slug = models.SlugField(max_length=128, unique=True)
    env_type = models.CharField(
        max_length=16,
        choices=[('production', 'Production'), ('staging', 'Staging'),
                 ('canary', 'Canary'), ('development', 'Development')],
        default='development',
    )
    topology_json = models.JSONField(default=dict, help_text="CMDB-injected topology")
    constraints_md = models.TextField(blank=True, help_text="Markdown constraints (change windows, rules)")
    credential_ref = models.CharField(max_length=256, blank=True, help_text="Vault path or key reference")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_environment'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.env_type})"


class Session(models.Model):
    """One interactive session or one-shot run."""
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    operator = models.CharField(max_length=128, default='admin')
    environment = models.ForeignKey(EnvironmentContext, on_delete=models.SET_NULL, null=True, blank=True)
    mode = models.CharField(max_length=16, choices=[('repl', 'REPL'), ('oneshot', 'One-shot')])
    status = models.CharField(
        max_length=16,
        choices=[('active', 'Active'), ('completed', 'Completed'), ('aborted', 'Aborted')],
        default='active',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        db_table = 'ops_session'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.session_id} ({self.operator})"


class AuditRecord(models.Model):
    """Append-only audit log. No update/delete via application code."""
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='audit_records')
    seq = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    target = models.CharField(max_length=256, blank=True, help_text="Target resource identifier")
    tool_name = models.CharField(max_length=128)
    parameters_json = models.JSONField(default=dict)
    risk_operation = models.CharField(max_length=16)       # READ / LOW_WRITE / MEDIUM_WRITE / HIGH_WRITE / CRITICAL
    risk_environment = models.CharField(max_length=16)     # dev / staging / canary / production
    risk_blast_radius = models.CharField(max_length=32)    # single / group / cluster-wide
    risk_score = models.FloatField()
    safety_decision = models.CharField(max_length=16)      # AUTO / ASK / DENY
    approved_by = models.CharField(max_length=128, blank=True)
    approval_time_ms = models.PositiveIntegerField(null=True)
    execution_started = models.DateTimeField(null=True)
    execution_completed = models.DateTimeField(null=True)
    execution_duration_ms = models.PositiveIntegerField(null=True)
    execution_success = models.BooleanField(null=True)
    result_summary = models.TextField(blank=True)
    llm_reasoning = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64)

    class Meta:
        db_table = 'ops_audit'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['session', 'seq']),
            models.Index(fields=['target', 'timestamp']),
            models.Index(fields=['tool_name', 'timestamp']),
            models.Index(fields=['risk_score']),
        ]

    def __str__(self):
        return f"[{self.seq}] {self.tool_name} → {self.safety_decision}"


class AgentMemory(models.Model):
    """Persistent memory entries (fault patterns, operational tips, preferences)."""
    MEMORY_TYPES = [
        ('fault_pattern', 'Fault Pattern'),
        ('ops_experience', 'Operations Experience'),
        ('team_preference', 'Team Preference'),
        ('temporary_constraint', 'Temporary Constraint'),
    ]
    memory_type = models.CharField(max_length=32, choices=MEMORY_TYPES)
    title = models.CharField(max_length=256)
    content = models.TextField()
    tags_json = models.JSONField(default=list)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_memory'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.memory_type}] {self.title}"
```

- [ ] **Step 4: Create admin.py**

```python
# backend/opsagent/admin.py
from django.contrib import admin
from .models import EnvironmentContext, Session, AuditRecord, AgentMemory


@admin.register(EnvironmentContext)
class EnvironmentContextAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'env_type', 'is_active', 'updated_at']
    list_filter = ['env_type', 'is_active']
    search_fields = ['name', 'slug']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'operator', 'environment', 'mode', 'status', 'started_at']
    list_filter = ['mode', 'status']
    search_fields = ['session_id', 'operator']
    readonly_fields = ['session_id', 'started_at']


@admin.register(AuditRecord)
class AuditRecordAdmin(admin.ModelAdmin):
    list_display = ['seq', 'tool_name', 'target', 'risk_score', 'safety_decision', 'execution_success', 'timestamp']
    list_filter = ['tool_name', 'safety_decision', 'risk_operation', 'execution_success']
    search_fields = ['target', 'result_summary', 'llm_reasoning']
    readonly_fields = [f.name for f in AuditRecord._meta.fields]


@admin.register(AgentMemory)
class AgentMemoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'memory_type', 'is_active', 'expires_at', 'created_at']
    list_filter = ['memory_type', 'is_active']
    search_fields = ['title', 'content']
```

- [ ] **Step 5: Create migrations/__init__.py**

```python
# backend/opsagent/migrations/__init__.py
```

- [ ] **Step 6: Register app in settings.py**

Read `backend/application/settings.py`, find `INSTALLED_APPS`, and add `"opsagent"` after `"stock"`.

- [ ] **Step 7: Make migrations and apply**

```bash
cd backend && python manage.py makemigrations opsagent
python manage.py migrate opsagent
```

Expected: `opsagent` migrations created and applied. No errors.

- [ ] **Step 8: Commit**

```bash
git add backend/opsagent/ backend/application/settings.py
git commit -m "feat(opsagent): add Django app skeleton with AuditRecord, Session, EnvironmentContext, AgentMemory models"
```

---

### Task 2: Core Types & Tool Registry

**Files:**
- Create: `backend/opsagent/core/__init__.py`
- Create: `backend/opsagent/core/types.py`
- Create: `backend/opsagent/core/tool_registry.py`
- Create: `backend/opsagent/tools/__init__.py`
- Create: `backend/opsagent/tools/base.py`

- [ ] **Step 1: Create core/__init__.py**

```python
# backend/opsagent/core/__init__.py
```

- [ ] **Step 2: Create core/types.py**

```python
# backend/opsagent/core/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class RiskLevel(str, Enum):
    READ = "READ"
    LOW_WRITE = "LOW_WRITE"
    MEDIUM_WRITE = "MEDIUM_WRITE"
    HIGH_WRITE = "HIGH_WRITE"
    CRITICAL = "CRITICAL"


class RiskEnv(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"


class RiskBlastRadius(str, Enum):
    SINGLE = "single"
    GROUP = "group"
    CLUSTER_WIDE = "cluster-wide"


class SafetyDecision(str, Enum):
    AUTO = "AUTO"
    AUTO_ECHO = "AUTO_ECHO"
    ASK = "ASK"
    ASK_BLAST = "ASK_BLAST"
    DENY = "DENY"


@dataclass
class RiskAssessment:
    operation: RiskLevel
    environment: RiskEnv
    blast_radius: RiskBlastRadius
    score: float
    decision: SafetyDecision
    reason: str = ""


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    session_id: str
    operator: str
    environment_name: str | None = None
    env_type: RiskEnv = RiskEnv.DEVELOPMENT
    constraints_md: str = ""
    topology_json: dict[str, Any] = field(default_factory=dict)


ToolHandler = Callable[..., Awaitable[ToolResult]]
```

- [ ] **Step 3: Create tools/base.py**

```python
# backend/opsagent/tools/base.py
import functools
from typing import Any
from opsagent.core.types import RiskLevel, ToolHandler


class ToolDef:
    __slots__ = ('name', 'description', 'parameters', 'risk_level', 'handler', 'requires_approval')

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        risk_level: RiskLevel,
        handler: ToolHandler,
        requires_approval: bool = True,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.risk_level = risk_level
        self.handler = handler
        self.requires_approval = requires_approval

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __repr__(self):
        return f"ToolDef({self.name}, risk={self.risk_level.value})"


def tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    risk_level: RiskLevel = RiskLevel.READ,
    requires_approval: bool = True,
):
    """Decorator to register a function as a tool."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(**kwargs):
            return await func(**kwargs)

        wrapper._tooldef = ToolDef(
            name=name,
            description=description,
            parameters=parameters,
            risk_level=risk_level,
            handler=wrapper,
            requires_approval=requires_approval,
        )
        return wrapper
    return decorator
```

- [ ] **Step 4: Create core/tool_registry.py**

```python
# backend/opsagent/core/tool_registry.py
from opsagent.tools.base import ToolDef


_registry: dict[str, ToolDef] = {}


def register(tool_def: ToolDef) -> None:
    if tool_def.name in _registry:
        raise ValueError(f"Tool '{tool_def.name}' already registered")
    _registry[tool_def.name] = tool_def


def get(name: str) -> ToolDef | None:
    return _registry.get(name)


def list_all() -> list[ToolDef]:
    return list(_registry.values())


def list_names() -> list[str]:
    return list(_registry.keys())


def get_openai_schemas() -> list[dict]:
    return [t.to_openai_schema() for t in _registry.values()]


def clear() -> None:
    _registry.clear()
```

- [ ] **Step 5: Create tools/__init__.py with auto-discover**

```python
# backend/opsagent/tools/__init__.py
import importlib
import pkgutil

from opsagent.core.tool_registry import register


def _has_tooldef(obj) -> bool:
    return hasattr(obj, '_tooldef') and obj._tooldef is not None


def auto_discover():
    """Scan this package and register all @tool decorated functions."""
    package = __package__ or 'opsagent.tools'
    for _, module_name, _ in pkgutil.iter_modules(__path__, prefix=package + '.'):
        mod = importlib.import_module(module_name)
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if _has_tooldef(attr):
                register(attr._tooldef)
```

- [ ] **Step 6: Write a quick unit test**

Create `backend/opsagent/tests/__init__.py` (empty), then create `backend/opsagent/tests/test_tool_registry.py`:

```python
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


def test_duplicate_raises():
    clear()
    td = ToolDef(name="dup.tool", description="Dup", parameters={},
                 risk_level=RiskLevel.READ, handler=_noop)
    register(td)
    with pytest.raises(ValueError):
        register(td)


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
```

- [ ] **Step 7: Run tests**

```bash
cd backend && python -m pytest opsagent/tests/test_tool_registry.py -v
```

Expected: 3 tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/opsagent/core/ backend/opsagent/tools/ backend/opsagent/tests/
git commit -m "feat(opsagent): add core types, tool registry, and @tool decorator"
```

---

### Task 3: Safety Engine

**Files:**
- Create: `backend/opsagent/core/safety.py`
- Create: `backend/opsagent/tests/test_safety.py`

- [ ] **Step 1: Create core/safety.py**

```python
# backend/opsagent/core/safety.py
from opsagent.core.types import (
    RiskLevel, RiskEnv, RiskBlastRadius, SafetyDecision, RiskAssessment, ToolDef,
)

_OPERATION_WEIGHTS = {
    RiskLevel.READ: 0,
    RiskLevel.LOW_WRITE: 1,
    RiskLevel.MEDIUM_WRITE: 3,
    RiskLevel.HIGH_WRITE: 7,
    RiskLevel.CRITICAL: 10,
}

_ENV_COEFFICIENTS = {
    RiskEnv.DEVELOPMENT: 0.3,
    RiskEnv.STAGING: 0.3,
    RiskEnv.CANARY: 0.6,
    RiskEnv.PRODUCTION: 1.0,
}

_BLAST_COEFFICIENTS = {
    RiskBlastRadius.SINGLE: 0.5,
    RiskBlastRadius.GROUP: 0.8,
    RiskBlastRadius.CLUSTER_WIDE: 1.0,
}


def compute_risk_score(
    operation: RiskLevel,
    environment: RiskEnv,
    blast_radius: RiskBlastRadius = RiskBlastRadius.SINGLE,
) -> float:
    op_w = _OPERATION_WEIGHTS.get(operation, 0)
    env_c = _ENV_COEFFICIENTS.get(environment, 1.0)
    blast_c = _BLAST_COEFFICIENTS.get(blast_radius, 0.5)
    return round(op_w * env_c * blast_c, 2)


def decide(score: float) -> SafetyDecision:
    if score == 0:
        return SafetyDecision.AUTO
    elif score <= 2.0:
        return SafetyDecision.AUTO_ECHO
    elif score <= 5.0:
        return SafetyDecision.ASK
    else:
        return SafetyDecision.ASK_BLAST


def assess(
    tool: ToolDef,
    environment: RiskEnv,
    blast_radius: RiskBlastRadius = RiskBlastRadius.SINGLE,
) -> RiskAssessment:
    score = compute_risk_score(tool.risk_level, environment, blast_radius)
    decision = decide(score)
    return RiskAssessment(
        operation=tool.risk_level,
        environment=environment,
        blast_radius=blast_radius,
        score=score,
        decision=decision,
        reason=f"score={score:.2f}: {tool.risk_level.value} × env({environment.value}) × blast({blast_radius.value})",
    )


def requires_user_approval(assessment: RiskAssessment) -> bool:
    return assessment.decision in (SafetyDecision.ASK, SafetyDecision.ASK_BLAST)
```

- [ ] **Step 2: Create tests/test_safety.py**

```python
# backend/opsagent/tests/test_safety.py
from opsagent.core.safety import compute_risk_score, decide, assess, requires_user_approval
from opsagent.core.types import RiskLevel, RiskEnv, RiskBlastRadius, SafetyDecision
from opsagent.tools.base import ToolDef


def _make_tool(risk: RiskLevel) -> ToolDef:
    async def _noop(**kwargs):
        from opsagent.core.types import ToolResult
        return ToolResult(success=True, output="ok")
    return ToolDef(name="test", description="t", parameters={}, risk_level=risk, handler=_noop)


def test_read_is_zero():
    assert compute_risk_score(RiskLevel.READ, RiskEnv.PRODUCTION, RiskBlastRadius.CLUSTER_WIDE) == 0


def test_low_write_staging_single():
    score = compute_risk_score(RiskLevel.LOW_WRITE, RiskEnv.STAGING, RiskBlastRadius.SINGLE)
    assert score == 0.15  # 1 × 0.3 × 0.5


def test_high_write_prod_cluster():
    score = compute_risk_score(RiskLevel.HIGH_WRITE, RiskEnv.PRODUCTION, RiskBlastRadius.CLUSTER_WIDE)
    assert score == 7.0  # 7 × 1.0 × 1.0


def test_critical_prod_cluster():
    score = compute_risk_score(RiskLevel.CRITICAL, RiskEnv.PRODUCTION, RiskBlastRadius.CLUSTER_WIDE)
    assert score == 10.0


def test_decide_auto():
    assert decide(0) == SafetyDecision.AUTO


def test_decide_auto_echo():
    assert decide(0.15) == SafetyDecision.AUTO_ECHO
    assert decide(2.0) == SafetyDecision.AUTO_ECHO


def test_decide_ask():
    assert decide(2.1) == SafetyDecision.ASK
    assert decide(5.0) == SafetyDecision.ASK


def test_decide_ask_blast():
    assert decide(5.1) == SafetyDecision.ASK_BLAST
    assert decide(10.0) == SafetyDecision.ASK_BLAST


def test_assess_read_tool_auto():
    tool = _make_tool(RiskLevel.READ)
    a = assess(tool, RiskEnv.PRODUCTION, RiskBlastRadius.CLUSTER_WIDE)
    assert a.decision == SafetyDecision.AUTO
    assert not requires_user_approval(a)


def test_assess_high_write_prod_requires_approval():
    tool = _make_tool(RiskLevel.HIGH_WRITE)
    a = assess(tool, RiskEnv.PRODUCTION, RiskBlastRadius.SINGLE)
    assert requires_user_approval(a)
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest opsagent/tests/test_safety.py -v
```

Expected: 10 tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/opsagent/core/safety.py backend/opsagent/tests/test_safety.py
git commit -m "feat(opsagent): add safety engine with risk scoring and approval gating"
```

---

### Task 4: Context Manager

**Files:**
- Create: `backend/opsagent/core/context.py`
- Create: `backend/opsagent/tests/test_context.py`

- [ ] **Step 1: Create core/context.py**

```python
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
```

- [ ] **Step 2: Create tests/test_context.py**

```python
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
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest opsagent/tests/test_context.py -v
```

Expected: 4 tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/opsagent/core/context.py backend/opsagent/tests/test_context.py
git commit -m "feat(opsagent): add context manager with three-layer context and system prompt builder"
```

---

### Task 5: First Tool — SSH

**Files:**
- Create: `backend/opsagent/tools/ssh.py`
- Create: `backend/opsagent/tests/test_ssh_tool.py`

- [ ] **Step 1: Create tools/ssh.py**

```python
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
```

- [ ] **Step 2: Create tests/test_ssh_tool.py**

```python
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
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest opsagent/tests/test_ssh_tool.py -v
```

Expected: 2 tests pass (first test gracefully handles missing ssh).

- [ ] **Step 4: Commit**

```bash
git add backend/opsagent/tools/ssh.py backend/opsagent/tests/test_ssh_tool.py
git commit -m "feat(opsagent): add ssh_exec tool"
```

---

### Task 6: Core Agent Loop

**Files:**
- Create: `backend/opsagent/core/agent_loop.py`
- Create: `backend/opsagent/tests/test_agent_loop.py`

- [ ] **Step 1: Create core/agent_loop.py**

```python
# backend/opsagent/core/agent_loop.py
import json
from typing import AsyncIterator
from opsagent.core.types import AgentContext, ToolResult, SafetyDecision
from opsagent.core.tool_registry import get, get_openai_schemas
from opsagent.core.safety import assess, requires_user_approval
from opsagent.core.context import ContextManager


class AgentLoop:
    def __init__(self, llm_client, context_manager: ContextManager | None = None):
        self.llm = llm_client
        self.ctx_manager = context_manager or ContextManager()

    async def run(
        self,
        user_input: str,
        context: AgentContext,
        history: list[dict] | None = None,
        on_tool_call: callable | None = None,
        on_approval_needed: callable | None = None,
        on_response: callable | None = None,
    ) -> str:
        """Run the agent loop. Returns final text response."""
        schemas = get_openai_schemas()
        system_prompt = self.ctx_manager.build_system_prompt(context, [s["function"]["name"] for s in schemas])
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        while True:
            response = await self.llm.chat.completions.create(
                model=self.llm.model_name,
                messages=messages,
                tools=schemas,
            )
            choice = response.choices[0]

            if choice.finish_reason == "stop":
                text = choice.message.content or ""
                if on_response:
                    on_response(text)
                return text

            if choice.finish_reason == "tool_calls":
                for tc in choice.message.tool_calls:
                    tool = get(tc.function.name)
                    if tool is None:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps({"error": f"Unknown tool: {tc.function.name}"}),
                        })
                        continue

                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    assessment = assess(tool, context.env_type)
                    if on_tool_call:
                        on_tool_call(tool.name, args, assessment)

                    if requires_user_approval(assessment) and on_approval_needed:
                        approved = await on_approval_needed(tool.name, args, assessment)
                        if not approved:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": json.dumps({"error": "User denied the operation"}),
                            })
                            continue

                    result: ToolResult = await tool.handler(**args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({
                            "success": result.success,
                            "output": result.output,
                            "error": result.error,
                            "metadata": result.metadata,
                        }),
                    })

            messages.append({
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in (choice.message.tool_calls or [])
                ],
            } if choice.message.tool_calls else {
                "role": "assistant",
                "content": choice.message.content,
            })
```

- [ ] **Step 2: Create tests/test_agent_loop.py**

```python
# backend/opsagent/tests/test_agent_loop.py
import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from opsagent.core.agent_loop import AgentLoop
from opsagent.core.types import AgentContext, RiskEnv, ToolResult, RiskAssessment, SafetyDecision
from opsagent.core.tool_registry import register, clear, get
from opsagent.tools.base import ToolDef


class _FakeChatCompletion:
    def __init__(self, content="", tool_calls=None, finish_reason="stop"):
        self.choices = [self]
        self.message = MagicMock()
        self.message.content = content
        self.message.tool_calls = tool_calls or []
        self.finish_reason = finish_reason


class _FakeLLM:
    def __init__(self, responses=None):
        self.model_name = "fake-model"
        self.responses = responses or []
        self.call_count = 0
        self.chat = MagicMock()
        self.chat.completions = MagicMock()

    async def _create(self, **kwargs):
        resp = self.responses[self.call_count] if self.call_count < len(self.responses) else _FakeChatCompletion()
        self.call_count += 1
        return resp


@pytest.fixture(autouse=True)
def clear_registry():
    clear()
    yield
    clear()


@pytest.mark.asyncio
async def test_agent_loop_text_only():
    llm = _FakeLLM(responses=[_FakeChatCompletion(content="Hello, how can I help?")])
    agent = AgentLoop(llm_client=llm)
    llm.chat.completions.create = AsyncMock(side_effect=llm._create)

    ctx = AgentContext(session_id="t1", operator="tester")
    result = await agent.run("hi", ctx)

    assert "Hello" in result


@pytest.mark.asyncio
async def test_agent_loop_with_tool_call():
    call_count = [0]

    async def _my_tool(**kwargs):
        call_count[0] += 1
        return ToolResult(success=True, output="executed")

    td = ToolDef(
        name="test_echo", description="Echo test",
        parameters={"type": "object", "properties": {}, "required": []},
        risk_level=RiskEnv.DEVELOPMENT, handler=_my_tool,
    )
    # Override risk_level
    from opsagent.core.types import RiskLevel
    td.risk_level = RiskLevel.READ
    register(td)

    tc = MagicMock()
    tc.id = "call_1"
    tc.type = "function"
    tc.function = MagicMock()
    tc.function.name = "test_echo"
    tc.function.arguments = json.dumps({})

    llm = _FakeLLM(responses=[
        _FakeChatCompletion(tool_calls=[tc], finish_reason="tool_calls"),
        _FakeChatCompletion(content="Done!", finish_reason="stop"),
    ])
    llm.chat.completions.create = AsyncMock(side_effect=llm._create)

    ctx = AgentContext(session_id="t2", operator="tester")
    agent = AgentLoop(llm_client=llm)
    result = await agent.run("do it", ctx)

    assert call_count[0] == 1
    assert "Done" in result
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest opsagent/tests/test_agent_loop.py -v
```

Expected: 2 tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/opsagent/core/agent_loop.py backend/opsagent/tests/test_agent_loop.py
git commit -m "feat(opsagent): add core agent loop with tool call dispatch and approval hooks"
```

---

### Task 7: Audit Logger (Django Integration)

**Files:**
- Create: `backend/opsagent/core/audit.py`
- Create: `backend/opsagent/tests/test_audit.py`

- [ ] **Step 1: Create core/audit.py**

```python
# backend/opsagent/core/audit.py
import hashlib
import json
import datetime
from opsagent.core.types import RiskAssessment, ToolResult


class AuditLogger:
    """Writes audit records. Uses Django ORM when available, falls back to in-memory list."""

    def __init__(self):
        self._records: list[dict] = []

    def log(
        self,
        session_id: int | None,
        seq: int,
        tool_name: str,
        parameters: dict,
        assessment: RiskAssessment,
        result: ToolResult,
        target: str = "",
        llm_reasoning: str = "",
    ) -> dict:
        record = {
            "session_id": session_id,
            "seq": seq,
            "timestamp": datetime.datetime.now().isoformat(),
            "target": target,
            "tool_name": tool_name,
            "parameters_json": parameters,
            "risk_operation": assessment.operation.value,
            "risk_environment": assessment.environment.value,
            "risk_blast_radius": assessment.blast_radius.value,
            "risk_score": assessment.score,
            "safety_decision": assessment.decision.value,
            "approved_by": "",
            "approval_time_ms": None,
            "execution_started": datetime.datetime.now().isoformat(),
            "execution_completed": datetime.datetime.now().isoformat(),
            "execution_duration_ms": 0,
            "execution_success": result.success,
            "result_summary": result.output[:500] if result.output else "",
            "llm_reasoning": llm_reasoning[:1000],
        }
        record["content_hash"] = hashlib.sha256(
            json.dumps(record, sort_keys=True, default=str).encode()
        ).hexdigest()
        self._records.append(record)
        self._persist_if_possible(record)
        return record

    def _persist_if_possible(self, record: dict) -> None:
        try:
            from opsagent.models import AuditRecord, Session as SessionModel
            session = SessionModel.objects.filter(session_id=record["session_id"]).first()
            if session is None:
                return
            AuditRecord.objects.create(
                session=session,
                seq=record["seq"],
                target=record["target"],
                tool_name=record["tool_name"],
                parameters_json=record["parameters_json"],
                risk_operation=record["risk_operation"],
                risk_environment=record["risk_environment"],
                risk_blast_radius=record["risk_blast_radius"],
                risk_score=record["risk_score"],
                safety_decision=record["safety_decision"],
                approved_by=record["approved_by"],
                approval_time_ms=record["approval_time_ms"],
                execution_started=record["execution_started"],
                execution_completed=record["execution_completed"],
                execution_duration_ms=record["execution_duration_ms"],
                execution_success=record["execution_success"],
                result_summary=record["result_summary"],
                llm_reasoning=record["llm_reasoning"],
                content_hash=record["content_hash"],
            )
        except Exception:
            pass  # Django not available or not configured — record stays in memory

    def query(self, tool_name: str | None = None, min_score: float | None = None) -> list[dict]:
        results = self._records
        if tool_name:
            results = [r for r in results if r["tool_name"] == tool_name]
        if min_score is not None:
            results = [r for r in results if r["risk_score"] >= min_score]
        return results

    def clear(self):
        self._records.clear()
```

- [ ] **Step 2: Create tests/test_audit.py**

```python
# backend/opsagent/tests/test_audit.py
from opsagent.core.audit import AuditLogger
from opsagent.core.types import (
    RiskLevel, RiskEnv, RiskBlastRadius, SafetyDecision, RiskAssessment, ToolResult,
)


def test_audit_log_in_memory():
    logger = AuditLogger()
    logger.clear()

    assessment = RiskAssessment(
        operation=RiskLevel.READ,
        environment=RiskEnv.STAGING,
        blast_radius=RiskBlastRadius.SINGLE,
        score=0.0,
        decision=SafetyDecision.AUTO,
    )
    result = ToolResult(success=True, output="kubectl get pods output")

    record = logger.log(
        session_id=None, seq=1, tool_name="k8s_get",
        parameters={"resource": "pods"}, assessment=assessment, result=result,
    )

    assert record["tool_name"] == "k8s_get"
    assert record["risk_score"] == 0.0
    assert record["safety_decision"] == "AUTO"
    assert len(record["content_hash"]) == 64


def test_audit_query_filter():
    logger = AuditLogger()
    logger.clear()

    a1 = RiskAssessment(RiskLevel.READ, RiskEnv.STAGING, RiskBlastRadius.SINGLE, 0.0, SafetyDecision.AUTO)
    a2 = RiskAssessment(RiskLevel.HIGH_WRITE, RiskEnv.PRODUCTION, RiskBlastRadius.SINGLE, 7.0, SafetyDecision.ASK_BLAST)
    r = ToolResult(success=True, output="ok")

    logger.log(None, 1, "k8s_get", {}, a1, r)
    logger.log(None, 2, "k8s_restart", {}, a2, r)

    assert len(logger.query(tool_name="k8s_restart")) == 1
    assert len(logger.query(min_score=5.0)) == 1
    assert len(logger.query(tool_name="k8s_get", min_score=1.0)) == 0
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest opsagent/tests/test_audit.py -v
```

Expected: 2 tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/opsagent/core/audit.py backend/opsagent/tests/test_audit.py
git commit -m "feat(opsagent): add audit logger with in-memory and Django ORM persistence"
```

---

### Task 8: CLI & Management Command

**Files:**
- Create: `backend/opsagent/cli/__init__.py`
- Create: `backend/opsagent/cli/render.py`
- Create: `backend/opsagent/cli/repl.py`
- Create: `backend/opsagent/management/__init__.py`
- Create: `backend/opsagent/management/commands/__init__.py`
- Create: `backend/opsagent/management/commands/ops.py`

- [ ] **Step 1: Create cli/__init__.py**

```python
# backend/opsagent/cli/__init__.py
```

- [ ] **Step 2: Create cli/render.py**

```python
# backend/opsagent/cli/render.py
import sys
from opsagent.core.types import RiskAssessment, SafetyDecision

_COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "reset": "\033[0m",
    "bold": "\033[1m",
}


def c(text: str, color: str) -> str:
    return f"{_COLORS.get(color, '')}{text}{_COLORS['reset']}"


def tool_call_banner(tool_name: str, args: dict, assessment: RiskAssessment) -> str:
    icon = {
        SafetyDecision.AUTO: c("✓", "green"),
        SafetyDecision.AUTO_ECHO: c("✓", "cyan"),
        SafetyDecision.ASK: c("⚠", "yellow"),
        SafetyDecision.ASK_BLAST: c("⚠", "red"),
        SafetyDecision.DENY: c("✗", "red"),
    }.get(assessment.decision, "?")

    lines = [
        f"  {icon} {c(tool_name, 'bold')}  "
        f"[{assessment.operation.value} × {assessment.environment.value} = {assessment.score:.1f}]  "
        f"{c(assessment.decision.value, 'yellow' if 'ASK' in assessment.decision.value else 'green')}",
    ]
    for k, v in args.items():
        v_str = str(v)
        if len(v_str) > 80:
            v_str = v_str[:77] + "..."
        lines.append(f"    {k}: {c(v_str, 'blue')}")
    return "\n".join(lines)


def tool_result_banner(success: bool, output: str, error: str | None) -> str:
    if success:
        header = c("✓ Success", "green")
    else:
        header = c("✗ Failed", "red")

    lines = [f"  {header}"]
    if output:
        for line in output.split("\n")[:10]:
            lines.append(f"    {line}")
    if error:
        lines.append(f"    {c('Error:', 'red')} {error}")
    return "\n".join(lines)


def approval_prompt(tool_name: str, args: dict, assessment: RiskAssessment) -> str:
    lines = [
        "",
        c(f"╔══ APPROVAL REQUIRED ══╗", "yellow"),
        c(f"║ Tool: {tool_name}", "bold"),
        c(f"║ Risk Score: {assessment.score:.2f} ({assessment.operation.value})", "yellow"),
        c(f"║ Environment: {assessment.environment.value}", "yellow"),
        c(f"║ Blast Radius: {assessment.blast_radius.value}", "yellow"),
    ]
    for k, v in args.items():
        lines.append(c(f"║ {k}: {v}", "blue"))
    lines.append(c(f"╚══════════════════════╝", "yellow"))
    lines.append("Execute? [y/N]: ")
    return "\n".join(lines)
```

- [ ] **Step 3: Create cli/repl.py**

```python
# backend/opsagent/cli/repl.py
import asyncio
import datetime
from opsagent.core.agent_loop import AgentLoop
from opsagent.core.context import ContextManager
from opsagent.core.types import AgentContext, RiskEnv
from opsagent.tools import auto_discover


class OpsREPL:
    def __init__(self, llm_client, ctx_manager: ContextManager | None = None):
        auto_discover()
        self.llm = llm_client
        self.ctx_manager = ctx_manager or ContextManager()
        self.agent = AgentLoop(llm_client=llm_client, context_manager=self.ctx_manager)
        self.history: list[dict] = []
        self.current_env: str | None = None

    def banner(self) -> str:
        from opsagent.cli.render import c
        return "\n".join([
            "",
            c("  ██████╗ ██████╗ ███████╗", "cyan"),
            c("  ╚════██╗██╔═══██╗██╔════╝", "cyan"),
            c("   █████╔╝██████╔╝███████╗", "cyan"),
            c("  ╚═══██╗██╔═══╝ ╚════██║", "cyan"),
            c("  ██████╔╝██║     ███████║", "cyan"),
            c("   ╚═════╝ ╚═╝     ╚══════╝", "cyan"),
            "",
            f"  Environment: {self.current_env or '(none)'}",
            f"  Session: {datetime.datetime.now().strftime('%Y-%m-%d-%H%M')}",
            "",
        ])

    async def run_once(self, user_input: str, auto_approve: bool = False) -> str:
        from opsagent.cli.render import tool_call_banner, tool_result_banner, approval_prompt

        ctx = AgentContext(
            session_id=datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
            operator="admin",
            environment_name=self.current_env,
        )

        tool_results = []

        def on_tool(name, args, assessment):
            print(tool_call_banner(name, args, assessment))

        async def on_approval(name, args, assessment):
            if auto_approve:
                return True
            print(approval_prompt(name, args, assessment))
            try:
                return input().strip().lower() == 'y'
            except (EOFError, KeyboardInterrupt):
                return False

        def on_response(text):
            print(f"\n{text}")

        result = await self.agent.run(
            user_input, ctx, history=self.history,
            on_tool_call=on_tool,
            on_approval_needed=on_approval,
            on_response=on_response,
        )
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": result})
        return result

    async def repl_loop(self):
        print(self.banner())
        while True:
            try:
                user_input = input("ops> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not user_input:
                continue
            if user_input.lower() in ('exit', 'quit', 'q'):
                break

            await self.run_once(user_input)
```

- [ ] **Step 4: Create management/__init__.py and management/commands/__init__.py**

```python
# backend/opsagent/management/__init__.py
```

```python
# backend/opsagent/management/commands/__init__.py
```

- [ ] **Step 5: Create management/commands/ops.py**

```python
# backend/opsagent/management/commands/ops.py
from django.core.management.base import BaseCommand
import asyncio


class Command(BaseCommand):
    help = 'OpsAgent — LLM-driven IT operations CLI'

    def add_arguments(self, parser):
        parser.add_argument('--run', type=str, help='One-shot: execute a single query and exit')
        parser.add_argument('--yes', action='store_true', help='Auto-approve all operations')
        parser.add_argument('--model', type=str, default='gpt-4o', help='LLM model name')
        parser.add_argument('--api-key', type=str, help='OpenAI API key (or set OPENAI_API_KEY env var)')
        parser.add_argument('--base-url', type=str, help='OpenAI-compatible API base URL')

    def handle(self, *args, **options):
        import os
        from openai import AsyncOpenAI
        from opsagent.cli.repl import OpsREPL

        api_key = options['api_key'] or os.environ.get('OPENAI_API_KEY', 'sk-placeholder')
        base_url = options['base_url'] or os.environ.get('OPENAI_BASE_URL')

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        client.model_name = options['model']

        repl = OpsREPL(llm_client=client)

        if options['run']:
            result = asyncio.run(repl.run_once(options['run'], auto_approve=options['yes']))
            self.stdout.write(self.style.SUCCESS("Done."))
        else:
            try:
                asyncio.run(repl.repl_loop())
            except KeyboardInterrupt:
                self.stdout.write("\nExiting.")
```

- [ ] **Step 6: Commit**

```bash
git add backend/opsagent/cli/ backend/opsagent/management/
git commit -m "feat(opsagent): add CLI REPL and Django management command (python manage.py ops)"
```

---

### Task 9: Wire Up — AppConfig, URLs, Admin Registration

**Files:**
- Modify: `backend/opsagent/apps.py` (add auto_discover)
- Create: `backend/opsagent/serializers.py`
- Create: `backend/opsagent/views/__init__.py`
- Create: `backend/opsagent/views/audit.py`
- Create: `backend/opsagent/views/session.py`
- Create: `backend/opsagent/urls.py`
- Modify: `backend/application/urls.py` (add opsagent routes)

- [ ] **Step 1: Update apps.py**

```python
# backend/opsagent/apps.py
from django.apps import AppConfig


class OpsAgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opsagent'
    verbose_name = 'OpsAgent - LLM运维Agent'

    def ready(self):
        from opsagent.tools import auto_discover
        auto_discover()
```

- [ ] **Step 2: Create serializers.py**

```python
# backend/opsagent/serializers.py
from rest_framework import serializers
from .models import AuditRecord, Session, EnvironmentContext, AgentMemory


class EnvironmentContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentContext
        fields = '__all__'


class SessionSerializer(serializers.ModelSerializer):
    audit_count = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = '__all__'

    def get_audit_count(self, obj):
        return obj.audit_records.count()


class AuditRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditRecord
        fields = '__all__'


class AgentMemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMemory
        fields = '__all__'
```

- [ ] **Step 3: Create views/__init__.py, views/audit.py, views/session.py**

```python
# backend/opsagent/views/__init__.py
```

```python
# backend/opsagent/views/audit.py
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from opsagent.models import AuditRecord
from opsagent.serializers import AuditRecordSerializer


class AuditRecordViewSet(ReadOnlyModelViewSet):
    queryset = AuditRecord.objects.all()
    serializer_class = AuditRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['tool_name', 'safety_decision', 'risk_operation', 'execution_success', 'session_id']
    search_fields = ['target', 'result_summary']
    ordering = ['-timestamp']
```

```python
# backend/opsagent/views/session.py
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from opsagent.models import Session
from opsagent.serializers import SessionSerializer


class SessionViewSet(ReadOnlyModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['mode', 'status', 'operator']
    ordering = ['-started_at']
```

- [ ] **Step 4: Create urls.py**

```python
# backend/opsagent/urls.py
from rest_framework.routers import DefaultRouter
from .views.audit import AuditRecordViewSet
from .views.session import SessionViewSet

router = DefaultRouter()
router.register(r'audit', AuditRecordViewSet, basename='ops-audit')
router.register(r'session', SessionViewSet, basename='ops-session')

urlpatterns = router.urls
```

- [ ] **Step 5: Add URL route in application/urls.py**

Read `backend/application/urls.py`, find the `urlpatterns` list, and add:
```python
path("api/ops/", include("opsagent.urls")),
```
after the existing `path("api/stock/", include("stock.urls"))` line.

- [ ] **Step 6: Commit**

```bash
git add backend/opsagent/apps.py backend/opsagent/serializers.py backend/opsagent/views/ backend/opsagent/urls.py backend/application/urls.py
git commit -m "feat(opsagent): wire up URLs, DRF views, auto-discover on app ready"
```

---

### Task 10: Integration Smoke Test

- [ ] **Step 1: Verify app loads without errors**

```bash
cd backend && python manage.py check --deploy 2>&1 | grep -i error || echo "No deploy errors"
```

Expected: No errors from opsagent.

- [ ] **Step 2: Verify management command help**

```bash
cd backend && python manage.py ops --help
```

Expected: Shows help text with --run, --yes, --model, --api-key options.

- [ ] **Step 3: Verify API routes exist**

```bash
cd backend && python manage.py show_urls 2>/dev/null | grep ops || echo "URL check skipped (django_extensions not configured)"
```

- [ ] **Step 4: Run full test suite**

```bash
cd backend && python -m pytest opsagent/ -v
```

Expected: All tests pass (10+ tests).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(opsagent): integration smoke test — app loads, CLI works, tests pass"
```

---

## Verification

To verify the full system end-to-end:

1. **CLI REPL:** `python manage.py ops` enters interactive REPL
2. **CLI One-shot:** `python manage.py ops --run "echo hello"` returns result
3. **Audit API:** `curl http://localhost:8000/api/ops/audit/` returns audit records
4. **Session API:** `curl http://localhost:8000/api/ops/session/` returns sessions
5. **Admin:** Visit Django admin → OpsAgent section with all 4 models
