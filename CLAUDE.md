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
| `views/apps/kline/` | K-line chart page (ECharts candlestick + trade markers + Donchian channel) |
| `views/signal/` | Daily signal views |
| `stores/` | Pinia stores (user, theme, routes, tags, permissions, dictionary, account) |
| `router/` | Route definitions (frontEnd.ts, backEnd.ts) |
| `utils/` | Helpers (request, auth, storage, websocket, format, theme) |
| `i18n/` | Internationalization (zh-cn, en) |
| `theme/` | SCSS theme system |

### API Routes

- `api/system/*` — RBAC system CRUD
- `api/stock/*` — Trading data endpoints
  - `contracts`, `strategy`, `position`, `closed-positions`, `trade_log`, `error_log`, `daily_signals`
  - `kline-data/` — K-line data, trade markers, available contracts
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

## Symbol Format Convention

All `symbol` fields across the system use the **exchange-prefixed format**: `{EXCHANGE}.{contract_code}` (e.g., `SHFE.rb2510`, `DCE.m2509`, `CZCE.MA501`).

- `FullContractList.symbol` — e.g., `SHFE.rb2510` (seed data: `SHFE.rb888` for continuous contract placeholder)
- `PositionState.symbol` — e.g., `SHFE.rb2510`
- `KlineData.symbol` — e.g., `SHFE.rb2510`
- `DailyStrategySignal.symbol` — e.g., `SHFE.rb2510`
- `ClosedPositionRecord.symbol` — e.g., `SHFE.rb2510`

**Why:** TqSDK API functions (`TargetPosTask`, `get_kline_serial`, `get_quote`, `get_position`) all require the exchange-prefixed format.

**Querying by product code:** Use the `product_code` field (bare code like `rb`, `MA`) for filtering by product family.

## Management Commands

| Command | Purpose |
|---------|---------|
| `sync_contracts` | Sync contract list from TqSDK, or `--seed` for seed data, `--repair-accounts` for missing accounts |
| `sync_kline` | Sync K-line data from TqSDK for active contracts |
| `sync_all` | Combined: contract sync + K-line sync in one step. Options: `--seed`, `--product rb,MA`, `--skip-kline`, `--skip-contract` |
| `fix_symbol_format` | Migrate DB symbols from bare format (`rb2510`) to exchange-prefixed (`SHFE.rb2510`) |
| `add_closed_position_menu` | Add closed position menu entry (RBAC setup) |
| `add_knowledge_base_menu` | Add knowledge base menu entry (RBAC setup) |

## Redis Distributed Lock

Located at `backend/stock/utils/redis_lock.py`. Provides:
- `redis_lock()` — context manager with auto-renewal (daemon thread renews every 15s)
- Default TTL: 30s (fast auto-release if process crashes)
- `LockAcquisitionError` — raised when lock cannot be acquired
- Used by: `tasks_daily_open.py` (per-account), `tasks_daily_close.py` (global), `tasks_exit_before_close.py` (global)

## K-line Chart Architecture

The K-line chart page (`web/src/views/apps/kline/`) uses **direct ECharts initialization** (not the `useECharts()` composable):

- `useKline.ts` manages chart lifecycle: `echarts.init()` → `setOption()` → `dispose()`
- Supports: candlestick, MA10/20/40 lines, Donchian channel (20HL), trade markers (entry/add-on/rollover/exit)
- dataZoom: slider at bottom + mouse wheel zoom + drag pan
- Legend: built-in ECharts legend for toggling MA and channel visibility
- Race condition protection: `fetchSeq` counter discards stale responses on fast contract switch

## Strategy Design Principles

### Entry Logic
- **Entry is purely based on 20HL Donchian channel breakout** (closing price breaking the 20-day high/low)
- No MA filter on entry — MA10/20/40 are **NOT** used to filter signals
- This is by design: prioritizes capturing all trend starts, uses stop-loss width for risk control instead of pre-filtering

### MA/Role of Trend Factor
- MA10/20/40 calculation is **only used for stop-loss distance adjustment**
- `trend_factor` (computed from MA gap ratio) dynamically adjusts stop-loss: 2.0 ATR (choppy) ~ 3.0 ATR (strong trend)
- The trend label (bull/bear/choppy) in signals and position state is informational only — it does NOT gate entry

### Key Design Difference from Backtest
- The backtest system (`backend/stock/backtest/`) is an independent offline analysis tool
- It includes additional MA filtering that the live system intentionally does not use
- Live system results will show slightly lower win rate (3~5%) but capture more trend trades

## Documentation

Knowledge base: `md/知识库/未命名/`
- `02-软件功能说明/` — Feature docs (strategy signals, performance, K-line buy points, position management)
- `04-策略设计文档/` — Strategy design docs
- `08-TODO/` — Issue tracking (all 42 issues resolved as of 2026-05-10)

## API Response Format Convention (重要!)

All custom API views (non-ModelViewSet) **MUST** wrap responses in the framework's standard envelope:

```python
return Response({
    'code': 2000,
    'msg': 'success',
    'data': { ... }
})
```

**Why:** The frontend axios interceptor (`web/src/utils/service.ts`) checks for `code` field. Missing it causes `"非标准返回"` error and blocks the response from reaching the page.

| Code | Meaning |
|------|---------|
| `2000` | Success |
| `4000` | Business error |
| `401` | Auth failure |
| `400` | Bad request |

**Note:** `ModelViewSet` routes auto-handle this wrapping. Custom `APIView` / `APIViewSet` classes must manually wrap — this is easy to miss and has caused repeated failures.

## Code Quality Status (2026-05-10)

All known issues resolved:
- 🔴 CRITICAL: 6/6 fixed
- 🟠 HIGH: 15/15 total (14 bug-items fixed, 1 verified as not-a-bug)
- 🟡 MEDIUM: 29/30 total (28 bug-items fixed, 1 verified not-a-bug, 1 TqSDK pending)
- 🟢 LOW: 7/9 total (7 fixed, 2 no-plan-to-fix)
