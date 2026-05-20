---
name: wechat-article-generator
description: >
  Generate WeChat public account articles for the FT trading system. Use this skill whenever the user asks to create, generate, or write a WeChat article, 公众号文章, or marketing content for any of the trading strategies (Turtle V2/V3, HVOB-MBI, original Turtle, or any strategy running on this system). Also use this skill when the user wants to "write an article" or "create content" about the trading system's performance, strategies, or features. This skill produces HTML files with inline styles that can be pasted directly into the WeChat public account editor.
---

# 微信公众号文章生成

## 核心原则

生成的文章是 **HTML 文件**，所有样式必须使用内联 `style=""`，因为微信公众号编辑器会剥离 CSS class。目标是：用户用浏览器打开 HTML → 全选复制 → 粘贴到公众号编辑器 → 微调发布。

## 数据来源

所有数据从 Django ORM 查询，位于 `backend/stock/models.py`：

| 模型 | 用途 | 关键字段 |
|------|------|----------|
| `TradingAccount` | 账户信息 | `name`, `current_equity`, `initial_balance` |
| `DailyEquitySnapshot` | 权益曲线 | `account__name`, `trade_date`, `balance`, `daily_return` |
| `ClosedPositionRecord` | 平仓交易 | `account__name`, `symbol`, `direction(1/-1)`, `pnl`, `exit_price`, `cost_price`, `holding_days` |
| `PositionState` | 当前持仓 | `account__name`, `symbol`, `units`, `direction(-1/0/1)` |
| `StrategyConfig` | 策略参数 | `account__name`, `skip_choppy_entry`, `protect_cost_enabled_ratio`, `position_risk_multiplier` |

注意：`TradingAccount` 的 `name` 字段存的是账号字符串（如 "510976"），不是 `account_number`。

## 文章结构

微信公众号文章通常包含以下模块，按实际策略数据灵活调整：

1. **引言** — 1-2段引出话题 + 对比表格吸引眼球
2. **策略简介** — 一句话定义 + 核心指标面板（权益/收益/回撤/天数）
3. **核心机制详解** — 策略的关键创新点，每个点配说明
4. **实盘数据** — 权益曲线(SVG) + 已平仓交易表 + 当前持仓
5. **对比分析** — 与原版或其他策略的维度对比表
6. **风险提示** — 胜率/回撤解释 + 趋势跟踪原理
7. **结语/方案建议** — 可选项

## 工作流

### Step 1: 理解策略

- 如果用户指定了策略名称（如 V2、V3、HVOB、原版），从数据库查询 StrategyConfig 和 TradingAccount 信息
- 如果用户没有指定，先问清楚：哪个策略？目标读者？文章风格（科普/技术干货/混合）？字数要求？

### Step 2: 查询数据

通过 Django ORM 查询以下数据：

```python
# 在 backend 目录下通过 Django shell 或 management command 执行
from stock.models import TradingAccount, DailyEquitySnapshot, ClosedPositionRecord, PositionState

# 账户信息
account = TradingAccount.objects.get(name='账号')

# 权益序列（按日期排序）
equity_qs = DailyEquitySnapshot.objects.filter(account=account).order_by('trade_date')

# 已平仓交易
trades_qs = ClosedPositionRecord.objects.filter(account=account).order_by('-executed_at')

# 当前持仓（units > 0）
positions_qs = PositionState.objects.filter(account=account, units__gt=0)
```

### Step 3: 生成 SVG 权益曲线

从 equity_qs 取 `trade_date` 和 `balance` 值，计算 SVG 参数：

- 找出 max_balance 和 min_balance
- 每天对应一根柱子，宽度18，间隔24
- 柱子高度映射到 [10, 130] 范围
- 日收益为正（daily_return > 0）→ 绿色 `#059669`，否则红色 `#dc2626`
- 生成 viewBox="0 0 340 190" 的 inline SVG

### Step 4: 构建文章内容

参考 `references/template-patterns.md` 中的 HTML 模式：

- 标题用 h2，子标题用 h3
- 数据展示用 table（不用 CSS grid/flex）
- 关键指标用统计面板（单行表格）
- 公式用 monospace 公式块
- 提示框用 callout（5种颜色可选）
- 方向用【多】/【空】文本标记
- 盈亏数据：正数 green `#059669`，负数 red `#dc2626`

### Step 5: 保存文件

1. 文件名：`策略简称-核心卖点-公众号文章.html`
2. 保存到 `wechat/`（项目根目录下的 wechat 文件夹）
3. 检查文件内容正确性

### Step 6: 更新索引

在 `wechat/README.md` 的文章列表追加新条目：

```markdown
### N. 文件名.html

- **标题：** 《文章标题》
- **发布日期：** YYYY-MM-DD
- **字数：** ~xxxx字
- **风格：** 科普型 / 技术干货型 / 混合型
- **公众号适配：** 全部内联样式，SVG图表，已优化可直接粘贴
- **内容概要：**
  策略核心要点速览...
```

## 设计规范

### 配色

| 用途 | 色值 |
|------|------|
| 主色 / 标题左边框 | `#2563eb` (蓝色) |
| 正收益 | `#059669` (绿色) |
| 负收益 | `#dc2626` (红色) |
| 正文文字 | `#444` |
| 标题文字 | `#1a1a1a` |
| 次要文字 | `#999` |
| 表格背景 | `#f8fafc` |
| 表格边框 | `#e8e8ee` |

### Callout 颜色约定

- 蓝色 `#eef3ff/#2563eb` — 定义、说明、一句话总结
- 绿色 `#ecfdf5/#059669` — 正面案例、实证
- 橙色 `#fff7ed/#d97706` — 重要提示、前置结论
- 紫色 `#f5f3ff/#7c3aed` — 深度分析、数学原理
- 红色 `#fef2f2/#dc2626` — 风险提示、免责声明

### 分隔线

节与节之间用 `◆ ◆ ◆` 分隔（居中、灰色、大间距）。

### Emoji 点缀

子标题可搭配 emoji 增强可读性：
- 🚀 核心机制
- 🛡️ 风控
- ⏰ 时间相关
- 🔄 循环/加仓
- 📊 数据

### 必须包含的元素

- 文章尾部风险提示（红色 callout）
- 底部 footer（FT 量化期货交易系统）
- 模拟盘声明（如适用）
- 数据日期

## 注意事项

1. 不要使用任何 CSS class 或 `<style>` 标签 — 全部内联
2. 不要使用 CSS Grid、Flexbox（display:flex 可用于 header 的 meta 行）
3. 不要使用 CSS 伪元素（::before, ::after）
4. SVG 必须是内联的（不是 img 标签引用外部文件）
5. 表格每列内容尽量简短，适配手机屏幕
6. 段落不要太长，手机阅读每段 2-4 行为宜
7. 数据要来自真实数据库查询，不要虚构
8. 文件保存前检查是否有未闭合的 HTML 标签
