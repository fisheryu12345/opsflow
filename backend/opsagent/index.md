# opsagent — 模块索引

> 上次自动更新: 2026-06-12

---

## `opsagent/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(opsagent): add Django app skeleton with AuditRecord, Se |
| `admin.py` | feat(opsagent): add Django app skeleton with AuditRecord, Session, EnvironmentCo | `EnvironmentContextAdmin`<br>`SessionAdmin`<br>`AuditRecordAdmin`<br>`AgentMemoryAdmin` |
| `apps.py` | feat(opsagent): wire up URLs, views, serializers, and AppConfig for OpsAgent | `OpsAgentConfig` |
| `models.py` | fix(opsagent): add error handling for missing API key and LLM connection failure | `EnvironmentContext` — Persisted OPS_CONTEXT.md equivalent — one row per managed environment.<br>`Session` — One interactive session or one-shot run.<br>`AuditRecord` — Append-only audit log. No update/delete via application code.<br>`AgentMemory` — Persistent memory entries (fault patterns, operational tips, preferences). |
| `serializers.py` | feat(opsagent): add local_exec tool, DeepSeek config defaults, web console, and  | `EnvironmentContextSerializer`<br>`SessionSerializer`<br>`AuditRecordSerializer`<br>`AgentMemorySerializer`<br>`TaskRunInputSerializer`<br>`TaskRunResultSerializer` |
| `urls.py` |  | feat(opsagent): add local_exec tool, DeepSeek config default |

## `opsagent\cli/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(opsagent): add CLI layer, REPL, render utilities, and D |
| `render.py` | feat(opsagent): add CLI layer, REPL, render utilities, and Django management com | `c()`<br>`tool_call_banner()`<br>`tool_result_banner()`<br>`approval_prompt()` |
| `repl.py` | fix(opsagent): add error handling for missing API key and LLM connection failure | `OpsREPL` |

## `opsagent\core/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(opsagent): add core types, tool registry, and tool base |
| `agent_loop.py` |  | `AgentLoopError` — Raised when the agent loop encounters a fatal error.<br>`AgentLoop` |
| `audit.py` | feat(opsagent): add AuditLogger with in-memory and Django ORM persistence | `AuditLogger` — Writes audit records. Uses Django ORM when available, falls back to in-memory list. |
| `context.py` | feat(opsagent): add ContextManager for three-layer context and system prompt | `ContextManager` — Manages the three-layer context (global / environment / session). |
| `safety.py` | feat(opsagent): add safety engine with risk scoring and approval decisions | `compute_risk_score()`<br>`decide()`<br>`assess()`<br>`requires_user_approval()` |
| `tool_registry.py` |  | `register()`<br>`get()`<br>`list_all()`<br>`list_names()`<br>`get_openai_schemas()`<br>`clear()` |
| `types.py` | feat(opsagent): add core types, tool registry, and tool base with auto-discover | `RiskLevel`<br>`RiskEnv`<br>`RiskBlastRadius`<br>`SafetyDecision`<br>`RiskAssessment`<br>`ToolResult` |

## `opsagent\management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(opsagent): add CLI layer, REPL, render utilities, and D |

## `opsagent\management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(opsagent): add CLI layer, REPL, render utilities, and D |
| `ops.py` | feat(opsagent): add local_exec tool, DeepSeek config defaults, web console, and  | `Command` |

## `opsagent\tests/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(opsagent): add core types, tool registry, and tool base |
| `test_agent_loop.py` | feat(opsagent): add AgentLoop core agent loop with tool dispatch and safety | `clear_registry()`<br>`test_agent_loop_text_only()`<br>`test_agent_loop_with_tool_call()` |
| `test_audit.py` | feat(opsagent): add AuditLogger with in-memory and Django ORM persistence | `test_audit_log_in_memory()`<br>`test_audit_query_filter()` |
| `test_context.py` | feat(opsagent): add ContextManager for three-layer context and system prompt | `test_build_context_defaults()`<br>`test_build_context_prod()`<br>`test_system_prompt_includes_tools()`<br>`test_system_prompt_includes_memory()` |
| `test_local_exec_tool.py` | feat(opsagent): add local_exec tool, DeepSeek config defaults, web console, and  | `test_local_exec_echo()`<br>`test_local_exec_failing_command()`<br>`test_local_exec_tooldef()` |
| `test_safety.py` | feat(opsagent): add safety engine with risk scoring and approval decisions | `test_read_is_zero()`<br>`test_low_write_staging_single()`<br>`test_high_write_prod_cluster()`<br>`test_critical_prod_cluster()`<br>`test_decide_auto()`<br>`test_decide_auto_echo()` |
| `test_ssh_tool.py` | feat(opsagent): add SSH tool for remote command execution via ssh_exec | `test_ssh_exec_localhost_echo()` — Test ssh_exec when ssh binary is not available (expected in test env).<br>`test_ssh_exec_tooldef_exists()` |
| `test_tool_registry.py` |  | `test_register_and_get()`<br>`test_duplicate_is_idempotent()`<br>`test_tool_decorator()` |

## `opsagent\tools/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | feat(opsagent): add core types, tool registry, and tool base with auto-discover | `auto_discover()` — Scan this package and register all @tool decorated functions. |
| `base.py` | feat(opsagent): add core types, tool registry, and tool base with auto-discover | `ToolDef`<br>`tool()` — Decorator to register a function as a tool. |
| `cmdb_tool.py` | CMDB query tool — Agent can query CMDB via natural language | `cmdb_query()` — Query CMDB configuration management database |
| `local_exec.py` | feat(opsagent): add local_exec tool, DeepSeek config defaults, web console, and  | `local_exec()` |
| `monitor_tool.py` | Monitor query tool — Agent can query alerts and monitoring metrics | `monitor_query()` — Query monitoring alerts and events |
| `opsflow_tool.py` | OpsFlow trigger tool — Agent can trigger OpsFlow template execution | `opsflow_trigger()` — Trigger or query OpsFlow workflow execution |
| `ssh.py` | feat(opsagent): add SSH tool for remote command execution via ssh_exec | `ssh_exec()` — Execute a command on a remote host via SSH. |

## `opsagent\views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(opsagent): wire up URLs, views, serializers, and AppCon |
| `audit.py` | feat(opsagent): wire up URLs, views, serializers, and AppConfig for OpsAgent | `AuditRecordViewSet` |
| `environment.py` | feat(opsagent): add local_exec tool, DeepSeek config defaults, web console, and  | `EnvironmentContextViewSet` |
| `memory.py` | feat(opsagent): add local_exec tool, DeepSeek config defaults, web console, and  | `AgentMemoryViewSet` |
| `run.py` |  | `TaskRunViewSet` |
| `session.py` | feat(opsagent): wire up URLs, views, serializers, and AppConfig for OpsAgent | `SessionViewSet` |
