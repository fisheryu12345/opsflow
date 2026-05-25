# 自定义管理命令说明

所有命令通过 `python manage.py <命令名> [参数]` 执行。

---

## 数据同步

### sync_contracts

从 TqSDK 同步期货合约列表到 `FullContractList` 表。

```bash
# 从 TqSDK 同步（需要 TqSDK 连接）
python manage.py sync_contracts

# 用内置种子数据初始化（TqSDK 不可用时使用）
python manage.py sync_contracts --seed

# 强制覆盖所有合约信息
python manage.py sync_contracts --force

# 修复缺少账户合约配置的账户
python manage.py sync_contracts --repair-accounts

# 为指定用户 ID 初始化默认品种（22 个主力合约）
python manage.py sync_contracts --activate-user=<用户ID>
```

### sync_kline

同步 K 线数据到 `KlineData` 表。

```bash
# 同步所有合约的全部 K 线
python manage.py sync_kline

# 指定品种（逗号分隔）
python manage.py sync_kline --product=rb,MA
```

### sync_all

合约 + K 线一站式同步。

```bash
# 全量同步
python manage.py sync_all

# 种子初始化 + K 线
python manage.py sync_all --seed

# 指定品种
python manage.py sync_all --product=rb,MA

# 跳过某一步
python manage.py sync_all --skip-kline
python manage.py sync_all --skip-contract
```

---

## 策略运行

### run_turtle

原版海龟交易系统 — 盘中实时监控唐奇安通道突破。

```bash
# 实时监控（主模式，Ctrl+C 退出）
python manage.py run_turtle --mode=monitor

# 单次检测（只检测信号，不执行）
python manage.py run_turtle --mode=once

# 强制平仓所有持仓
python manage.py run_turtle --mode=exit_only
```

- 最大仓位 3 个单位（原版海龟为 4）
- 入场：20 日唐奇安通道突破
- 出场：10 日反向突破 / 2N 硬止损
- 加仓：0.5N 间隔，最多 3 单位
- 定时重启：8:55 / 13:25 / 20:55

### hvob_trading

HVOB-MBI 高波动突破日内交易系统（位于 `hvob_mbi` 模块）。

```bash
# 启动交易引擎（需指定账户）
python manage.py hvob_trading --account=10

# 观察模式（只记录信号，不下单）
python manage.py hvob_trading --account=10 --dry-run
```

- 纯日内策略，不过夜
- 开盘区间(OR)跟踪 → 突破判定 → 时间衰减 → 收盘强平

### compare_atr_periods

比较 14/20/26 三种 ATR 周期对 trend_factor 分布的影响。

```bash
# 生成对比 HTML 报告
python manage.py compare_atr_periods --output=report.html
```

---

## 账户管理

### reset_accounts

账户重置 — 平仓 → 清理全部数据 → 重置权益 → 可选激活实盘。

```bash
# 先备份（必须！）
python manage.py dumpdata stock hvob_mbi > backup_$(date +%Y%m%d_%H%M%S).json

# 重置指定账户（需要 TqSDK 连接用于平仓）
python manage.py reset_accounts --account=1,5,6,10

# 跳过 TqSDK 平仓（收盘后无行情时使用）
python manage.py reset_accounts --account=1,5,6,10 --skip-exit

# 重置全部活跃账户
python manage.py reset_accounts --all

# 重置 + 设置初始权益 502000
python manage.py reset_accounts --account=1,5,6,10 --initial-balance=502000

# 重置 + 激活 V2 实盘模式
python manage.py reset_accounts --account=1,5,6,10 --activate-live
```

**清理范围（全部删除，不可恢复）：**
| 表 | 说明 |
|------|------|
| `PositionState` | 持仓记录 |
| `DailyStrategySignal` | 所有信号 |
| `DailyEquitySnapshot` | 权益快照 |
| `RollingPerformanceMetrics` | 滚动指标 |
| `SymbolDailyPnl` | 品种日盈亏 |
| `AccountPerformanceSummary` | 账户绩效汇总 |
| `TradeLog` | 交易日志 |
| `ErrorLog` | 错误日志 |
| `ClosedPositionRecord` | 历史已平仓 |
| `SlippageRecord` | 滑点记录 |
| `HvobMbiDailyState` | HVOB 运行状态 |
| `HvobMbiWatchlistItem` | HVOB 观察池 |

**保留的配置表：** `StrategyConfig`、`AccountContractConfig`、`FullContractList`、`KlineData`、`HvobMbiConfig`

---

## 执行顺序建议

```
                ┌─────────────────┐
                │  初始化部署顺序    │
                └─────────────────┘

1. sync_contracts --seed        # 初始化合约
2. sync_contracts --activate-user # 分配账户品种
3. sync_kline                    # 下载 K 线

                ┌─────────────────┐
                │  实盘切换顺序      │
                └─────────────────┘

1. dumpdata 备份                  # 备份数据库
2. reset_accounts --skip-exit    # 清理数据
3. 开盘后 reset_accounts          # 有行情时平仓(可选)

                ┌─────────────────┐
                │  日常运行          │
                └─────────────────┘

- run_turtle --mode=monitor      # 海龟策略
- hvob_trading --account=10      # HVOB 策略
```
