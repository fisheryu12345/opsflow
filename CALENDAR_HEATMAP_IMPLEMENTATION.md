# 日历热力图功能实现说明

## 📅 功能概述

在Dashboard的品种胜率统计图表下方，新增了一个**交易日收益热力图**，以日历形式直观展示每个交易日的收益率分布情况。

## 🎯 技术实现

### 1. 后端API (`backend/stock/views/performance.py`)

**新增视图类**: `DailyReturnsCalendarView`

```python
class DailyReturnsCalendarView(viewsets.ViewSet):
    """
    【日历热力图数据接口】
    
    💡 用途：
    - 为前端日历热力图提供日收益率数据
    - 按月份分组，便于 ECharts heatmap 渲染
    
    📊 返回格式：
    {
        "code": 2000,
        "msg": "success",
        "data": [
            {
                "date": "2024-01-15",
                "daily_return": 1.25,
                "month": 1,
                "day": 15,
                "year": 2024
            },
            ...
        ]
    }
    """
```

**数据来源**: `DailyEquitySnapshot` 模型的 `trade_date` 和 `daily_return` 字段

### 2. 路由配置 (`backend/stock/urls.py`)

```python
path('daily-returns-calendar/', daily_returns_calendar_view, name='daily-returns-calendar')
```

**访问地址**: `GET /api/stock/daily-returns-calendar/?account=1`

### 3. 前端API封装 (`web/src/views/system/home/api.ts`)

```typescript
export function getDailyReturnsCalendar(accountId: number) {
	return request.get<{
		code: number;
		msg: string;
		data: Array<{
			date: string;
			daily_return: number;
			month: number;
			day: number;
			year: number;
		}>;
	}>(`/api/stock/daily-returns-calendar/?account=${accountId}`);
}
```

### 4. 前端图表实现 (`web/src/views/system/home/index.vue`)

**模板结构**:
```vue
<!-- 日历热力图 - 占据全宽且高度加倍 -->
<el-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24" class="grid-item-wrapper">
    <div class="grid-card-item grid-large-item grid-animation14 chart-container">
        <div ref="calendarHeatmapRef" class="chart-ref"></div>
    </div>
</el-col>
```

**初始化函数**: `initCalendarHeatmap()`

**核心逻辑**:
1. 从后端获取日收益率数据
2. 转换为 ECharts heatmap 格式：`[month, day, value]`
3. 配置颜色映射（红绿渐变）
4. 响应式布局适配

## 🎨 视觉效果

### 颜色映射规则

| 收益率范围 | 颜色 | 含义 |
|-----------|------|------|
| > 5% | 🔴 深红 | 大幅盈利 |
| 1% ~ 5% | 🔴 浅红 | 小幅盈利 |
| -1% ~ 1% | ⚪ 白色 | 基本持平 |
| -5% ~ -1% | 🟢 浅绿 | 小幅亏损 |
| < -5% | 🟢 深绿 | 大幅亏损 |

### 布局特点

- **X轴**: 日期（1-31日）
- **Y轴**: 月份（1月-12月）
- **单元格**: 每个格子代表一个交易日
- **Tooltip**: 悬停显示具体日期和收益率
- **响应式**: 
  - 桌面端：显示所有标签
  - 移动端：简化标签，每5天显示一个

## 📊 数据示例

```json
{
    "code": 2000,
    "msg": "success",
    "data": [
        {"date": "2026-04-30", "daily_return": 0, "month": 4, "day": 30, "year": 2026},
        {"date": "2026-05-01", "daily_return": 0, "month": 5, "day": 1, "year": 2026},
        {"date": "2026-05-06", "daily_return": 0.08, "month": 5, "day": 6, "year": 2026},
        {"date": "2026-05-07", "daily_return": 0.95, "month": 5, "day": 7, "year": 2026}
    ]
}
```

## ✅ 测试验证

### 后端测试

```bash
curl "http://localhost:8000/api/stock/daily-returns-calendar/?account=1"
```

**预期结果**: 返回JSON格式的日收益率数据数组

### 前端测试

1. 访问: `http://localhost:8081`
2. 导航到 Dashboard 首页
3. 在"品种胜率统计"下方查看"交易日收益热力图"
4. 悬停单元格查看具体收益率

## 🔧 技术要点

### ECharts Heatmap 配置

```javascript
// 数据转换
const heatmapData = calendarData.map(item => [
    item.month - 1,  // ECharts月份从0开始
    item.day - 1,    // ECharts日期从0开始
    item.daily_return
]);

// 颜色映射
visualMap: {
    min: -5,
    max: 5,
    inRange: {
        color: ['#16a34a', '#4ade80', '#f3f4f6', '#fb7185', '#dc2626']
    }
}
```

### 响应式设计

- **字体大小**: 使用 `getResponsiveFontConfig()` 动态计算
- **标签间隔**: 移动端每5天显示一个标签
- **网格间距**: 根据屏幕宽度自适应调整

## 📝 注意事项

1. **数据完整性**: 如果某日无交易，该日不会出现在热力图中
2. **年份处理**: 当前显示最新年份的数据，多年数据会混合显示
3. **性能优化**: 数据量较大时（超过1年），建议添加年份筛选功能
4. **颜色感知**: 红色代表盈利，绿色代表亏损（符合A股习惯）

## 🚀 未来优化方向

1. **多年度支持**: 添加年份切换器，支持查看不同年份的热力图
2. **交互增强**: 点击单元格跳转到当日详细数据
3. **统计信息**: 在图表上方显示月度汇总统计（最佳/最差交易日）
4. **导出功能**: 支持将热力图导出为图片

---

**实施完成时间**: 2026-05-07  
**相关PR**: 待创建
