# CLAUDE.md

Quantitative futures trading system on django-vue3-admin. Integrates TqSDK for market data and execution.

**Stack:** Python 3.11+ / Django 4.2.7 / DRF 3.14 / MySQL / Redis / Celery | Vue 3 / TypeScript / Vite 4 / Element Plus / Pinia / ECharts | TqSDK / APScheduler

## Getting Started

```bash
# Backend
cd backend && cp conf/env.example.py conf/env.py  # edit DB config
pip install -r requirements.txt && python manage.py migrate
python manage.py init && python manage.py init_area
python manage.py runserver 0.0.0.0:8000

# Frontend
cd web && npm install --registry=https://registry.npm.taobao.org
npm run dev    # localhost:8080
npm run build  # production
```

**Default credentials:** superadmin / admin123456

## Architecture

### Backend Modules

| Directory | Purpose |
|-----------|---------|
| `application/` | Django project config, Celery, routing |
| `conf/` | Environment config (DB, Redis, feature flags) |
| `dvadmin/system/` | RBAC framework (users, roles, menus, depts) |
| `dvadmin/utils/` | Shared utilities (viewsets, serializers, pagination, middleware) |
| `stock/` | **Trading app** — models, scheduler, views, TqSDK integration |
| `stock/scheduler/` | APScheduler jobs (open/close, ATR, performance) |
| `stock/deepseek/` | AI trade analysis |
| `plugins/` | Plugin system |

### Stock Models (backend/stock/models.py)

1. **Infrastructure:** `TradingAccount`, `FullContractList`, `StrategyConfig`
2. **Signal:** `DailyStrategySignal`
3. **Performance (3-tier):** `DailyEquitySnapshot` → `RollingPerformanceMetrics` → `AccountPerformanceSummary`
4. **State:** `PositionState`, `ClosedPositionRecord`
5. **Logging:** `ErrorLog`, `TradeLog`

### Frontend Modules (web/src/)

| Directory | Purpose |
|-----------|---------|
| `api/` | Axios API clients |
| `components/` | Shared components (auth, table, editor, etc.) |
| `layout/` | App shell (nav, menu, tags, breadcrumb, lock screen) |
| `views/system/` | RBAC pages (login, user, role, menu, dept, config, logs) |
| `views/apps/` | Trading pages (positions, contracts, strategy config, trade logs, error logs) |
| `views/apps/kline/` | K-line chart (ECharts candlestick + Donchian channel) |
| `views/signal/` | Daily signal views |
| `stores/` | Pinia stores |
| `router/` | Route definitions |
| `utils/` | Helpers (request, auth, websocket, format) |
| `i18n/` | Internationalization |
| `theme/` | SCSS theme |

### API Routes

- `api/system/*` — RBAC CRUD
- `api/stock/*` — Trading data: `contracts`, `strategy`, `position`, `closed-positions`, `trade_log`, `error_log`, `daily_signals`, `kline-data/`, performance endpoints
- `api/login/`, `api/logout/`, `api/captcha/`, `api/token/` — Auth
- Swagger at `/`

### Key Config Files

- `backend/conf/env.py` — DB, Redis, debug, captcha
- `backend/application/settings.py` — Django/DRF/JWT/CORS/Celery
- `backend/stock/parameter_config.py` — Trading params (risk, ATR, gap protection)
- `web/.env` / `web/.env.development` — Frontend env

## Common Tasks

### New trading feature
1. Model in `stock/models.py` → `makemigrations && migrate`
2. ViewSet in `stock/views/`, serializer in `stock/serializers/`
3. Route in `stock/urls.py`
4. (Optional) FastCRUD in `web/src/api/` + view in `web/src/views/apps/`

### Scheduler tasks
Jobs live in `backend/stock/scheduler/`. Use `redis_lock()` for concurrent safety.

## Symbol Format Convention

All `symbol` fields use exchange-prefixed format `{EXCHANGE}.{contract_code}` (e.g., `SHFE.rb2510`, `DCE.m2509`, `CZCE.MA501`). This applies to `FullContractList`, `PositionState`, `KlineData`, `DailyStrategySignal`, `ClosedPositionRecord`.

**Why:** TqSDK APIs (`TargetPosTask`, `get_kline_serial`, `get_quote`, `get_position`) require this format.

Query by product: use `product_code` field (bare code like `rb`, `MA`).

## Management Commands

| Command | Purpose |
|---------|---------|
| `sync_contracts` | Sync contracts from TqSDK (`--seed`, `--repair-accounts`) |
| `sync_kline` | Sync K-line data |
| `sync_all` | Combined sync (`--seed`, `--product rb,MA`, `--skip-*`) |
| `fix_symbol_format` | Migrate bare symbols to exchange-prefixed |
| `add_closed_position_menu` / `add_knowledge_base_menu` | RBAC menu setup |

## Redis Distributed Lock

`backend/stock/utils/redis_lock.py` — context manager with auto-renewal (15s daemon thread, 30s TTL). Raises `LockAcquisitionError`. Used by open/close/exit scheduler tasks.

## K-line Chart

Direct ECharts init at `web/src/views/apps/kline/` (not `useECharts()` composable). `useKline.ts` manages lifecycle: `init()` → `setOption()` → `dispose()`. Supports candlestick, MA10/20/40, Donchian 20HL, trade markers, dataZoom slider + wheel, legend toggles. Uses `fetchSeq` counter for stale-response protection.

## Strategy Design Principles

- **Entry:** Pure 20HL Donchian channel breakout (closing price breaks 20-day high/low). No MA filter — captures all trend starts, controls risk via stop-loss width.
- **MA/Trend Factor:** MA10/20/40 only used for stop-loss distance adjustment. `trend_factor` dynamically adjusts stop-loss width (2.0 ATR choppy ~ 3.0 ATR strong trend). Trend labels are informational only.
- **Backtest difference:** Backtest (`backend/stock/backtest/`) is an independent offline tool with extra MA filtering. Live system omits it intentionally — expect ~3-5% lower win rate but more trend trades.
- **Position sizing discrepancy (TURTLE vs V2/V3):** TURTLE (_turtle_unit_lots) uses `equity × 1% / (2×N×multiplier)` with `int()` floor — same contract can yield different lot counts than V2/V3 which use fixed `risk_per_unit=4000` with `round()`. Both are intentional per strategy design. See `md/知识库/未命名/04-策略设计文档/策略设计-原版海龟对比组.md` "实盘示例：rb2610 仓位差异".
- **Add-on window no exit:** Add-on operations (`execute_add_on_order`) do not update `cost_price` (weighted average). No exit occurs between add-on and daily close — the daily close job syncs `cost_price` from TqSDK's `open_price_long`/`open_price_short`, so PnL is unaffected.
- **Open price at 9:02:** Open-position tasks run at 9:02. At that point `quote.last_price` already reflects the opening price after call auction. The gap-protection logic using `last_price` is correct.
- **Signal uniqueness per day per symbol:** `DailyStrategySignal` is computed once per symbol per day. `unique_together = ('account', 'symbol', 'trade_date')` 不含 `trade_type` 仍不会产生重复，原因如下:

  收盘任务(15:32)对每个账户的按序执行: `check_breakout_signal(ENTRY)` → `check_exit_signals(STOP_LOSS)` → `check_add_position_signals(ADD_ON)` → `check_rollover_signals(ROLLOVER)`。

  - ENTRY 要求 `units=0`（无持仓），其他三类均要求 `units>0`（有持仓）→ **ENTRY 与其余互斥**
  - STOP_LOSS 与 ADD_ON 价格方向相反 → **逻辑互斥**
  - ROLLOVER 仅主力合约切换日触发（低频事件），与 STOP_LOSS/ADD_ON 在时间上几乎不重叠。即使重叠，`check_duplicate_pending_signal` 已防止同类型重复，而不同信号类型在同一个 symbol 上同时生成不会产生逻辑冲突。因此 `trade_type` 不需要加入唯一约束。
- **Domestic commodity futures only:** This system is designed for Chinese commodity futures (SHFE, DCE, CZCE, CFFEX, INE). Contract code patterns, regex parsing, session times, and exchange rules all assume the Chinese futures market.

> **Strategy notes:** Add strategy logic clarifications discovered during bug fixes as bullet points above. This keeps the design rationale visible for future work.


## Documentation

Knowledge base: `md/知识库/未命名/`
- `02-软件功能说明/` — Feature docs
- `04-策略设计文档/` — Strategy design
- `08-TODO/` — Issue tracking (all resolved as of 2026-05-10)

## API Response Format (重要!)

Custom API views (non-ModelViewSet) **MUST** wrap responses:
```python
return Response({'code': 2000, 'msg': 'success', 'data': { ... }})
```
Missing `code` field triggers `"非标准返回"` error in frontend axios interceptor (`web/src/utils/service.ts`).

| Code | Meaning |
|------|---------|
| `2000` | Success |
| `4000` | Business error |
| `401` | Auth failure |
| `400` | Bad request |

ModelViewSet routes auto-handle wrapping. Custom `APIView` / `APIViewSet` must manually wrap.

## Logging Convention (重要!)

**Do NOT use** `logger.info/warning/error`. Use these DB-persisting functions instead:

- **`log_trade(function_name, msg, symbol='N/A', log_level='INFO', account=None)`**
- **`log_error(function_name, msg, account=None)`**

Define a module-level `FSM = 'my_function_name'` constant and reuse it in all calls.

## Bug Fixes

When fixing a bug, document it with background, effect, suggestion in the TODO list, then update the list after fixing.
