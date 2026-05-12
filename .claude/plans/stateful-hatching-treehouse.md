# 添加"最大回撤恢复天数"到 Dashboard

## Context

用户希望在 Dashboard 首页的"平均滑点/有利滑点率"卡片右侧新增一个"最大回撤恢复天数"指标卡片。

**什么是最大回撤恢复天数？**
从回撤谷底（净值最低点）恢复到前期净值高点所需的天数。区别于已有的 `max_drawdown_duration`（最大回撤持续天数，衡量从峰值跌到谷底的时间），恢复天数衡量的是从谷底爬回峰值的时间，反映策略的恢复能力。

## Changes

### Step 1: Model — `backend/stock/models.py` 添加字段

在 `AccountPerformanceSummary` 的 `max_drawdown_duration` 字段后（line 484）新增：

```python
max_drawdown_recovery_days = models.IntegerField("最大回撤恢复天数", default=0,
    help_text="历史上从回撤谷底恢复到前期高点所需的最长天数（仅统计完整回撤周期）")
```

`default=0` 确保存量记录兼容，无需特殊处理。

### Step 2: Migration

```bash
python manage.py makemigrations stock
python manage.py migrate stock
```

### Step 3: 计算逻辑 — `backend/stock/core/performance.py`

`update_account_summary()` 函数中（line 270-311），当前变量只追踪了 `drawdown_start_date`（回撤起始日），需要新增 `trough_date` 跟踪谷底日期。

具体改动：

1. **初始化**（line 275-277）：增加 `max_dd_recovery_days = 0; trough_date = None; running_trough_equity = None`
2. **回撤中分支**（line 295-298）：当 `drawdown_start_date` 首次设置时，同时初始化 `trough_date = trade_date`；后续 equity 新低时更新 `trough_date`
3. **新高/恢复分支**（line 279-288、299-305）：从 `trough_date` 到恢复日期计算 `recovery_days_trough`，更新 `max_dd_recovery_days`
4. **`update_or_create` defaults**（line 424）：增加 `'max_drawdown_recovery_days': max_dd_recovery_days`

### Step 4: Serializer — `backend/stock/serializers/serializers.py`

`AccountPerformanceSummarySerializer.Meta.fields` 中，在 `'max_drawdown_duration'` 后（line 244）添加 `'max_drawdown_recovery_days'`。

### Step 5: 前端类型 — `web/src/views/system/home/api.ts`

`AccountSummary` 接口中，在 `max_drawdown_duration` 后（line 53）添加 `max_drawdown_recovery_days: number`。

### Step 6: 前端 Dashboard — `web/src/views/system/home/index.vue`

`buildNormalItems()` 函数中（line 266），在 slippage 卡片 push 之后、`return items` 之前增加新卡片：

```typescript
items.push({
    number: 18,
    label: '最大回撤恢复天数',
    value: `${summary.max_drawdown_recovery_days}天`,
    colorType: summary.max_drawdown_recovery_days <= 5 ? 'positive' : summary.max_drawdown_recovery_days <= 20 ? 'neutral' : 'negative',
    tooltip: '历史上从回撤谷底恢复到前期高点所需的最长天数。天数越短说明策略恢复能力越强'
});
```

颜色阈值：<=5天绿色（快速恢复）、<=20天中性、>20天红色（恢复缓慢）。

## Verification

1. Run migration
2. Trigger `update_account_summary()` via daily close task or manually
3. Check that `GET /api/stock/account-summaries/` returns `max_drawdown_recovery_days`（查看浏览器改价)
4. 等一下，我看看它的展示是什么样的

Maybe I should first look at the card layout? Let me just make the changes.

