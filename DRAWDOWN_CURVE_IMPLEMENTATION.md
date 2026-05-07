# 资金回撤曲线图功能实现说明

## 📅 功能概述

在Dashboard的资金曲线图表下方，新增了一个**资金回撤百分比曲线图**，直观展示账户在不同时间点的风险暴露程度和回撤情况。

## 🎯 技术实现

### 1. 后端API (`backend/stock/views/performance.py`)

**新增视图类**: `DrawdownCurveView`

```python
class DrawdownCurveView(viewsets.ViewSet):
    """
    【资金回撤曲线数据接口】
    
    💡 用途：
    - 为前端提供资金回撤百分比时间序列数据
    - 用于绘制回撤曲线图，直观展示风险暴露程度
    
    🔢 计算逻辑：
    - peak_equity: 到当前日期为止的历史最高权益
    - drawdown_pct: (当前权益 - 历史最高权益) / 历史最高权益 * 100%
    - is_new_peak: 是否创出新高（用于标记关键时间点）
    """
```

**数据来源**: `DailyEquitySnapshot` 模型的 `trade_date` 和 `balance` 字段

**核心算法**:
```python
peak_equity = Decimal('0')
for snapshot in snapshots:
    current_equity = snapshot['balance']
    
    # 更新历史最高权益
    if current_equity > peak_equity:
        peak_equity = current_equity
        is_new_peak = True
    else:
        is_new_peak = False
    
    # 计算回撤百分比
    drawdown_pct = (current_equity - peak_equity) / peak_equity * 100
```

### 2. 路由配置 (`backend/stock/urls.py`)

```python
path('drawdown-curve/', drawdown_curve_view, name='drawdown-curve')
```

**访问地址**: `GET /api/stock/drawdown-curve/?account=1`

### 3. 前端API封装 (`web/src/views/system/home/api.ts`)

```typescript
export function getDrawdownCurve(accountId: number) {
	return request.get<{
		code: number;
		msg: string;
		data: Array<{
			date: string;
			equity: number;
			peak_equity: number;
			drawdown_pct: number;
			is_new_peak: boolean;
		}>;
	}>(`/api/stock/drawdown-curve/?account=${accountId}`);
}
```

### 4. 前端图表实现 (`web/src/views/system/home/index.vue`)

**模板结构**:
```vue
<!-- 资金回撤曲线 - 占据全宽且高度加倍 -->
<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="grid-item-wrapper">
    <div class="grid-card-item grid-large-item grid-animation16 chart-container">
        <div ref="drawdownCurveRef" class="chart-ref"></div>
    </div>
</el-col>
```

**初始化函数**: `initDrawdownCurveChart()`

**核心特性**:
- Y轴只显示负值区域（最大值为0）
- 颜色分级显示不同严重程度的回撤
- 标注最大回撤位置
- 标记创出新高的时间点

---

## 🎨 视觉效果

### 颜色映射规则

| 回撤范围 | 颜色 | 含义 |
|---------|------|------|
| < -10% | 🔴 深红 | 严重回撤 |
| -10% ~ -5% | 🔴 浅红 | 中度回撤 |
| -5% ~ -2% | 🟠 橙色 | 轻度回撤 |
| -2% ~ 0% | ⚪ 灰色 | 正常波动 |

### 图表特点

- **Y轴**: 回撤百分比（负值，最大值=0）
- **X轴**: 交易日期
- **面积填充**: 红色渐变，强调风险区域
- **MarkLine**: 虚线标注最大回撤位置
- **MarkPoint**: 绿色圆点标记创出新高的时间点
- **Tooltip**: 悬停显示具体日期、回撤百分比和风险等级图标

### 响应式设计

- **桌面端**: 完整标签显示，较大符号尺寸
- **移动端**: 简化日期格式（MM-DD），较小符号尺寸

---

## 📊 数据示例

```json
{
    "code": 2000,
    "msg": "success",
    "data": [
        {
            "date": "2026-04-30",
            "equity": 997978.14,
            "peak_equity": 997978.14,
            "drawdown_pct": 0.0,
            "is_new_peak": true
        },
        {
            "date": "2026-05-01",
            "equity": 997978.14,
            "peak_equity": 997978.14,
            "drawdown_pct": 0.0,
            "is_new_peak": false
        },
        {
            "date": "2026-05-06",
            "equity": 998820.14,
            "peak_equity": 998820.14,
            "drawdown_pct": 0.0,
            "is_new_peak": true
        }
    ]
}
```

---

## ✅ 测试验证

### 后端测试

```bash
curl "http://localhost:8000/api/stock/drawdown-curve/?account=1"
```

**预期结果**: 
- ✅ 状态码: 200
- ✅ 返回JSON格式的日回撤数据数组
- ✅ 包含 date, equity, peak_equity, drawdown_pct, is_new_peak 字段

### 前端测试

1. 访问: `http://localhost:8081`
2. 导航到 Dashboard 首页
3. 滚动到"资金曲线"下方查看"资金回撤曲线"
4. 悬停曲线查看具体回撤百分比

---

## 🔧 技术要点

### ECharts 配置亮点

#### 1. **动态Y轴范围**
```javascript
yAxis: {
    max: 0,  // 最大值固定为0
    min: Math.floor(maxDrawdown * 1.2)  // 最小值根据实际数据动态调整
}
```

#### 2. **颜色分级映射**
```javascript
visualMap: {
    pieces: [
        { lte: -10, color: '#dc2626' },   // 严重回撤
        { gt: -10, lte: -5, color: '#fb7185' },  // 中度回撤
        { gt: -5, lte: -2, color: '#fbbf24' },   // 轻度回撤
        { gt: -2, lte: 0, color: '#94a3b8' }     // 正常波动
    ]
}
```

#### 3. **最大回撤标注**
```javascript
markLine: {
    data: [{
        yAxis: maxDrawdown  // 自动定位到最低点
    }]
}
```

#### 4. **新高标记**
```javascript
markPoint: {
    data: drawdownData
        .filter(item => item.is_new_peak)
        .map(item => ({
            coord: [dates.indexOf(item.date), item.drawdown_pct],
            value: '新高'
        }))
}
```

### 回撤计算逻辑

**核心公式**:
```
回撤百分比 = (当前权益 - 历史最高权益) / 历史最高权益 × 100%
```

**关键特性**:
1. **单调递增的峰值追踪**: `peak_equity` 只会增加不会减少
2. **回撤始终为负或零**: 当权益创新高时，回撤为0%
3. **相对比例计算**: 使用百分比而非绝对值，便于跨账户对比

---

## 📝 业务价值

### 1. **风险监控**
- 实时识别账户风险暴露程度
- 快速定位严重回撤的时间段
- 评估策略的风险控制能力

### 2. **策略优化**
- 分析回撤发生的原因（市场波动 vs 策略缺陷）
- 对比不同时期的回撤特征
- 优化止损和仓位管理参数

### 3. **心理建设**
- 帮助交易者理解回撤是正常现象
- 建立对策略的信心（看到历史回撤后的恢复）
- 避免在回撤期恐慌性平仓

---

## 🚀 未来优化方向

1. **多周期对比**: 添加20日/60日滚动最大回撤曲线
2. **恢复时间标注**: 标注从最大回撤恢复到新高的天数
3. **阈值告警**: 当回撤超过设定阈值时发送通知
4. **分品种回撤**: 按品种分组展示回撤贡献度
5. **导出报告**: 支持将回撤分析导出为PDF报告

---

**实施完成时间**: 2026-05-07  
**相关PR**: 待创建
