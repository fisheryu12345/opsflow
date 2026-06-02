# CLAUDE.md

Full-stack application with django-vue3-admin. Includes ops workflow engine.

**Stack:** Python 3.11+ / Django 4.2.7 / DRF 3.14 / MySQL / Redis / Celery | Vue 3 / TypeScript / Vite 4 / Element Plus / Pinia / ECharts | TqSDK / APScheduler

## Quick Start

```bash
cd backend && cp conf/env.example.py conf/env.py  # edit DB config
pip install -r requirements.txt && python manage.py migrate
python manage.py runserver 0.0.0.0:8000

cd web && npm install && npm run dev  # localhost:8080
```

**Credentials:** superadmin / yupei1986

## Project Rules

- Do what's asked; nothing more, nothing less
- NEVER create files unless necessary — prefer editing existing files
- NEVER create doc files unless explicitly requested
- ALWAYS read a file before editing it; keep files under 500 lines
- Validate input at system boundaries; NEVER commit secrets/.env files
- NEVER add `Co-Authored-By` trailer to commits
- ALWAYS run tests after code changes; verify build succeeds before committing

## Architecture

- **Backend:** Django apps under `stock/` (trading), `dvadmin/` (RBAC), `opsflow/` (ops),
  `plugins/` — config in `conf/env.py`, settings in `application/settings.py`
- **Frontend:** `web/src/views/apps/` (trading pages), `views/system/` (RBAC),
  `api/` (axios clients), `stores/` (Pinia), `router/`, `utils/`
- **API:** `api/stock/*` (trading data), `api/system/*` (RBAC), `api/opsflow/*`
- All `symbol` fields use exchange-prefixed format `{EXCHANGE}.{contract_code}` (e.g. `SHFE.rb2510`)
- Redis distributed lock: `stock/utils/redis_lock.py` — auto-renewal, 30s TTL

## API Response Convention

Custom views **MUST** wrap: `return Response({'code': 2000, 'msg': 'success', 'data': {...}})`
| Code | Meaning |
|------|---------|
| `2000` | Success | `4000` | Business error | `401` | Auth | `400` | Bad request |

ModelViewSets auto-wrap; custom `APIView`/`APIViewSet` must wrap manually.

## Logging Convention

**Do NOT use** `logger.*`. Use `log_trade(fsm_name, msg, ...)` / `log_error(fsm_name, msg)` instead.
Define module-level `FSM = 'my_func_name'` constant for reuse.

## Agent Coordination

Named agents message each other via `SendMessage`. Spawn all in one message.

| Pattern | Flow | Use |
|---------|------|-----|
| **Pipeline** | A→B→C→D | Feature dev |
| **Fan-out** | Lead→A,B,C→Lead | Independent research |
| **Supervisor** | Lead↔workers | Complex refactor |

**Routing:** 3 tiers — Agent Booster (WASM) / Haiku / Sonnet+Opus.
Swarm YES for 3+ files, new features, cross-module refactoring.
Swarm NO for single edits, fixes, docs, config, questions.

**Before task:** `memory search --query "[keywords]" --namespace patterns`
**After success:** `memory store --namespace patterns --key "[name]" --value "[what worked]"`

## Key MCP Tools

| Category | Tools |
|----------|-------|
| Memory | `memory_store`, `memory_search`, `memory_search_unified` |
| Swarm | `swarm_init`, `swarm_status`, `swarm_health` |
| Agents | `agent_spawn`, `agent_list`, `agent_status` |
| Security | `aidefence_scan`, `aidefence_is_safe` |
| Hooks | `hooks_route`, `hooks_post-task` |

## Bug Fixes

Document each bug fix with background, effect, suggestion in the TODO list.

## OPSflow Style Guide

See [OPSFLOW.md](OPSFLOW.md) — design tokens, animations, dialog styling, naming conventions.
