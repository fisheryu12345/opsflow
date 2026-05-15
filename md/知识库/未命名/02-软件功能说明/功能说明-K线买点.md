# K线买点功能说明

## 功能概述

K线买点模块在K线图上可视化展示策略交易信号（入场、加仓、移仓、平仓），并结合唐奇安通道和均线系统辅助分析。用于复盘策略执行过程、验证信号生成逻辑、排查漏单/误单。

---

## 页面结构

```
┌──────────────────────────────────────────────────────────────────┐
│  筛选栏: [合约选择] [开始日期] [结束日期] [查询]                    │
├──────────────────────────────────────────────────────────────────┤
│  K线图区域                                                        │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  图例: K线 MA10 MA20 MA40 通道上轨 通道下轨               │    │
│  │  入场(绿针) 加仓(蓝圈) 移仓(橙钻) 平仓(红针)              │    │
│  ├──────────────────────────────────────────────────────────┤    │
│  │  ┃  ┃                                                     │    │
│  │  ┃  │  ▲  入场  ┃                                        │    │
│  │  ┃──│─────────│──┃  MA10 ───                              │    │
│  │  ┃  │  ● 加仓  ┃  MA20 ---                                │    │
│  │  ┃  │    ◆ 移仓  ┃  通道上轨 - -                           │    │
│  │  ┃  ▼        ┃  通道下轨 - -                           │    │
│  │  ┃     ▼ 平仓  ┃                                           │    │
│  ├──────────────────────────────────────────────────────────┤    │
│  │  ◀━━━━━━━━━━━━━━━ dataZoom 滑块 ━━━━━━━━━━━━━━━▶         │    │
│  └──────────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────┤
│  交易明细表格                                                     │
│  ┌────────┬────────┬────────┬────────┬──────────────────────┐   │
│  │  日期   │  类型   │  价格   │  方向   │  说明                │   │
│  ├────────┼────────┼────────┼────────┼──────────────────────┤   │
│  │05-08   │入场    │3275.00 │ 多头   │开仓 1 Unit @ 3275.00  │   │
│  │05-10   │加仓    │3320.00 │ 多头   │加仓 1 Unit @ 3320.00  │   │
│  │05-15   │平仓    │3450.00 │ 多头   │多头平仓 2手 盈亏+145.00│   │
│  └────────┴────────┴────────┴────────┴──────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 标记类型

| 类型 | 代码 | 图表样式 | 数据来源 | 说明 |
|------|------|---------|---------|------|
| 入场 | `ENTRY` | 绿色图钉 `pin` | `DailyStrategySignal` (SUCCESS) | 唐奇安通道突破开仓 |
| 加仓 | `ADD_ON` | 蓝色圆圈 `circle` | `DailyStrategySignal` (SUCCESS) | 金字塔加仓 |
| 移仓 | `ROLLOVER` | 橙色菱形 `diamond` | `DailyStrategySignal` (SUCCESS) | 主力合约换月 |
| 平仓 | `EXIT` | 红色图钉 `pin` | `ClosedPositionRecord` | 止损/止盈平仓 |

### 价格来源

- **入场**: 使用 `signal_direction` 决定价格 — 多头用唐奇安上轨(`donchian_upper`)，空头用唐奇安下轨(`donchian_lower`)
- **加仓/移仓**: 使用该交易日的K线收盘价
- **平仓**: 使用 `ClosedPositionRecord.exit_price`

---

## 设计逻辑

### 1. 入场买点 — 唐奇安通道突破

```
条件: 收盘价突破20日唐奇安通道
  多头突破: close > prior_20_day_high  → signal_direction = 1
  空头突破: close < prior_20_day_low   → signal_direction = -1
前提: 
  - 当前品种无持仓 (units = 0)
  - 无未执行的 ENTRY 信号 (防重复)
  - 趋势因子与突破方向一致 (choppy 趋势下双向可开)
```

唐奇安通道计算：
```
prior_20_day_high = max(high[-21:-1])   # 前20根K线的最高价
prior_20_day_low  = min(low[-21:-1])    # 前20根K线的最低价
```

### 2. 加仓买点 — 海龟金字塔加仓

```
规则:
  1单位持仓时:
    - 价格向有利方向移动 0.5×ATR  → 加1单位
    - 价格向有利方向移动 1.0×ATR  → 加2单位 (直接满仓)
  2单位持仓时:
    - 从首次开仓价累计移动 1.0×ATR → 加1单位
  最大总持仓: 3单位

  多头基准: latest_price - first_open_price（统一基准）
  空头基准: first_open_price - latest_price（统一基准）
```

### 3. 止损价格 — 动态跟踪止损

```
多头止损:
  stop_loss = highest_close - 2 × ATR_20
  
空头止损:
  stop_loss = lowest_close + 2 × ATR_20

其中:
  highest_close = max(持仓期间每日收盘价)
  lowest_close  = min(持仓期间每日收盘价)
  ATR_20        = 20日平均真实波幅

触发条件: 
  多头: 最新收盘价 < 止损价
  空头: 最新收盘价 > 止损价
```

### 4. 移仓换月

```
触发条件:
  - PositionState.is_rollover_needed = True
  - PositionState.units > 0

执行流程:
  1. 平掉旧主力合约持仓 (TargetPosTask → 0)
  2. 在新主力合约上开等量仓位
  3. 初始化新合约的止损参数 (基于20日历史数据)
  4. 删除旧 PositionState，创建新 PositionState
```

### 5. 跳空保护

```
跳空幅度检查 (开仓前):
  多头: gap_up = (latest_price - pre_close) / ATR
        如果 gap_up > 1.5×ATR → 拦截 (禁止买入)
  空头: gap_down = (pre_close - latest_price) / ATR
        如果 gap_down > 1.5×ATR → 拦截 (禁止卖出)

反向跳空 (多头遇低开、空头遇高开) 视为有利，不拦截。
```

---

## 买点生成流程

```
交易日 15:00 收盘后 (tasks_daily_close):
  1. sync_contract_list_from_tqsdk()  ← 更新主力合约
  2. sync_kline_data_from_tqsdk()     ← 同步K线
  3. calculate_indicators()           ← 计算指标 (ATR, MA, 唐奇安通道)
  4. check_breakout_signal()          ← 检测突破 → ENTRY信号
  5. check_add_position_signals()     ← 检测加仓 → ADD_ON信号
  6. update_stop_loss() / check_exit() ← 止损检查 → STOP_LOSS信号
  7. check_rollover_signals()         ← 移仓检查 → ROLLOVER信号

交易日 21:02/09:02 开盘 (tasks_daily_open):
  1. process_signals_by_type('STOP_LOSS')  ← 先止损
  2. process_signals_by_type('ENTRY')      ← 再开仓
  3. process_signals_by_type('ROLLOVER')   ← 移仓
  4. process_signals_by_type('ADD_ON')     ← 最后加仓
```

---

## 关键指标

| 指标 | 用途 | 计算方式 |
|------|------|---------|
| ATR(20) | 波动率度量、止损/加仓基准 | 20日真实波幅均值 |
| MA(10) | 短期趋势 | 10日收盘价均值 |
| MA(20) | 中期趋势 | 20日收盘价均值 |
| MA(40) | 长期趋势 | 40日收盘价均值 |
| 唐奇安通道(20HL) | 突破信号基准 | 20日最高价/最低价 |
| 趋势因子 | 趋势强度量化 | MA间距归一化 |

---

## 数据流

```
TqSDK K线数据
  │
  ├──→ sync_kline_data_from_tqsdk() → KlineData 表 → K线图展示
  │
  └──→ calculate_indicators()
          │
          ├──→ 计算 ATR
          ├──→ 计算 MA10/20/40
          ├──→ 计算 唐奇安通道
          └──→ 检测突破信号
                  │
                  └──→ DailyStrategySignal (PENDING)
                          │
                          └──→ process_signals_by_type()
                                  │
                                  ├──→ 成功 → executed_status = SUCCESS → TradeMarkers 显示
                                  ├──→ 失败 → executed_status = FAILED
                                  └──→ 取消 → executed_status = CANCELLED (跳空保护等)
```

---

## 关联功能

- [信号监控](./功能说明-信号监控.md) — 信号列表与执行状态追踪
- [持仓管理](./功能说明-持仓管理.md) — 当前持仓与止损管理
- [策略配置](策略设计-海龟增强V2交易全流程.md) — 策略参数配置
