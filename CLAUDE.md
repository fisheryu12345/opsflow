# CLAUDE.md

Full-stack application with django-vue3-admin. Includes ops workflow engine.

**Stack:** Python 3.11+ / Django 4.2.7 / DRF 3.14 / MySQL / Redis / Celery | Vue 3 / TypeScript / Vite 4 / Element Plus / Pinia / ECharts | APScheduler

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
- **Code language:** All code strings MUST be in English. Only comments use bilingual (Chinese + English) format.
- **No emoji in DB:** NEVER store emoji characters in MySQL backend — filter or replace them before saving. MySQL (utf8mb3) does not support 4-byte Unicode (emoji).
- **Stray files forbidden:** NEVER run `python -c "..."` with inline code containing `{}` — bash expands them and creates stray files. Always use `python << 'EOF' ... EOF` heredoc instead.
- **NO direct git commit/push:** Every single code submission MUST go through the `/opsflow-commit` skill. **Crucially:** the `/opsflow-commit` skill must NEVER be auto-invoked by Claude as part of a response. It is ONLY invoked when the user explicitly types `/opsflow-commit` in the chat. No programmatic triggering, no "顺便提交", no end-of-task auto-commit.

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

## Project Standards

Key standards reference files (loaded on demand):
- [Frontend Style Guide](docs/guides/frontend-style-guide.md) — SCSS, Vue, i18n, TS, Buttons, Pinia
- [Project & Engineering Standards](docs/guides/project-standards.md) — Architecture, API response, Backend layers, Error handling
- [Process & Governance Standards](docs/guides/process-standards.md) — Git, Docs, Design constraints
