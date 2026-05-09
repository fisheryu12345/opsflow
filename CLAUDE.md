# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **quantitative futures trading system** built on the django-vue3-admin framework. It manages trading strategies, positions, risk parameters, and performance analytics for commodity futures. The system integrates with TqSDK for real-time market data and trade execution.

**Tech Stack:**
- **Backend:** Python 3.11+, Django 4.2.7, Django REST Framework 3.14, MySQL, Redis, Celery, Channels/WebSocket
- **Frontend:** Vue 3 (Composition API + TypeScript), Vite 4, Element Plus, Pinia, FastCRUD, ECharts
- **Trading:** TqSDK (天勤量化), APScheduler

## Getting Started

### Backend (backend/)

```bash
cd backend
cp conf/env.example.py conf/env.py  # Edit database config
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py init              # Initialize RBAC data
python manage.py init_area         # Initialize region data
python manage.py runserver 0.0.0.0:8000
```

### Frontend (web/)

```bash
cd web
npm install --registry=https://registry.npm.taobao.org
npm run dev       # Dev server at http://localhost:8080
npm run build     # Production build
npm run lint-fix  # ESLint fix
```

**Default credentials:** superadmin / admin123456

## Architecture

### Backend Modules

| Directory | Purpose |
|-----------|---------|
| `application/` | Django project config (settings, URLs, ASGI/WSGI, Celery, routing) |
| `conf/` | Environment config (database, Redis, feature flags) |
| `dvadmin/system/` | RBAC framework (users, roles, menus, depts, permissions, dicts) |
| `dvadmin/utils/` | Shared utilities (viewsets, serializers, pagination, middleware, permissions, filters) |
| `stock/` | **Trading application** (models, scheduler, views, serializers, TqSDK integration) |
| `stock/scheduler/` | APScheduler jobs for daily trading tasks (open/close, ATR, performance) |
| `stock/deepseek/` | AI integration for trade analysis |
| `plugins/` | Plugin system for add-on modules |

### Stock App Data Models (backend/stock/models.py)

The models follow a layered architecture:

1. **Infrastructure Layer:** `TradingAccount`, `FullContractList` (contract metadata/switch), `StrategyConfig` (parametrized strategy settings)
2. **Signal Layer:** `DailyStrategySignal` (breakout signals, trend state)
3. **Performance Layer (3-tier):** `DailyEquitySnapshot` → `RollingPerformanceMetrics` → `AccountPerformanceSummary`
4. **State Management:** `PositionState` (current positions, stop-loss, add-on tracking), `ClosedPositionRecord` (closed trades)
5. **Logging:** `ErrorLog`, `TradeLog`

### Frontend Modules (web/src/)

| Directory | Purpose |
|-----------|---------|
| `api/` | Axios API clients grouped by domain |
| `components/` | Shared components (auth, table, editor, icon, import, cropper) |
| `layout/` | App shell (nav bars, tags view, menu, breadcrumb, footer, lock screen) |
| `views/` | Page components by feature |
| `views/system/` | RBMA pages (home, login, user, role, menu, dept, dict, config, logs) |
| `views/apps/` | Trading app pages (positions, contracts, strategy config, trade logs, closed positions, error logs) |
| `views/signal/` | Daily signal views |
| `stores/` | Pinia stores (user, theme, routes, tags, permissions, dictionary) |
| `router/` | Route definitions (frontEnd.ts, backEnd.ts) |
| `utils/` | Helpers (request, auth, storage, websocket, format, theme) |
| `i18n/` | Internationalization (zh-cn, en) |
| `theme/` | SCSS theme system |

### API Routes

- `api/system/*` — RBAC system CRUD
- `api/stock/*` — Trading data endpoints
  - `contracts`, `strategy`, `position`, `closed-positions`, `trade_log`, `error_log`, `daily_signals`
  - Performance: `equity-snapshots`, `rolling-metrics`, `account-summaries`, `symbol-win-rate`, `cumulative-stats`, `daily-returns-calendar`, `drawdown-curve`
- `api/login/`, `api/logout/`, `api/captcha/`, `api/token/` — Auth
- Swagger docs at `/`

### Key Configuration Files

- `backend/conf/env.py` — Database, Redis, debug, captcha settings
- `backend/application/settings.py` — Django/DRF/SimpleJWT/CORS/Celery config
- `backend/stock/parameter_config.py` — Trading parameters (risk, ATR, trend factor, gap protection)
- `web/.env` — Frontend environment variables
- `web/.env.development` — Dev environment

## Common Tasks

### Create new Django app (trading feature)
1. Create app structure under `backend/stock/` with `views/`, `serializers/`, etc.
2. Define model in `backend/stock/models.py`, run `makemigrations && migrate`
3. Create ViewSet in `backend/stock/views/`, serializer in `backend/stock/serializers/`
4. Register route in `backend/stock/urls.py`
5. If using FastCRUD: create CRUD definition in `web/src/api/` and view in `web/src/views/apps/`

### Docker deployment
```bash
docker-compose up -d
docker exec -ti dvadmin-django bash -c "python manage.py makemigrations && python manage.py migrate && python manage.py init_area && python manage.py init"
```

### Scheduler tasks (APScheduler)
Scheduled trading tasks live in `backend/stock/scheduler/`. Jobs handle daily open/close, ATR calculation, performance snapshots, and report sending.
