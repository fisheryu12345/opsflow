# ITSM Tab 排序优化与默认首页调整

> 提交: db14a792 | 日期: 2026-07-05
> 涉及 App: itsm
> 类型: 功能优化

---

## 背景

ITSM 页面 tab 原本的排序不够合理：
1. 默认首页是"工单"（tickets），但用户更频繁使用的是"服务市场"（service-market）作为入口
2. tab 分组混杂——用户功能（工单、看板）与管理后台（SLA、技能组、路由、升级）混在一起
3. "服务市场"（sort: 15）和"服务目录管理"（sort: 22）插在 dashboard（10）和 tickets（20）之间，不符合使用直觉

## 实现方案

### 核心设计

重新排定 ITSM 所有 tab 的 sort 值，按"用户核心流程 → 后台管理 → 遗留模块"三段式分组：

| sort | Tab | 分组 | 说明 |
|------|-----|------|------|
| 10 | 服务市场 | **核心流程** | 设为默认首页 |
| 20 | 工单 | | 高频访问 |
| 30 | 看板 | | 数据总览 |
| 40 | 流程模板 | | 流程定义管理 |
| 50 | 服务目录管理 | **ITSM 管理** | 后台配置 |
| 60 | SLA | | |
| 70 | 技能组 | | |
| 80 | 排班 | | |
| 90 | 路由 | | |
| 100 | 升级 | | |
| 110 | 委托 | | |
| 120 | 事件 | **遗留模块** | 低频率 |
| 130 | 变更 | | |

### 关键代码

**数据层：** `backend/iam/management/commands/seed_iam_page_configs.py` 中更新 `itsm_tabs` 数组：

```python
itsm_tabs = [
    {'key': 'service-market', ..., 'is_default': True,  'sort': 10},  # 改为默认
    {'key': 'tickets',       ..., 'is_default': False, 'sort': 20},
    {'key': 'dashboard',     ..., 'is_default': False, 'sort': 30},
    {'key': 'workflows',     ...,                      'sort': 40},
    # ── ITSM 管理 ──
    {'key': 'service-admin', ...,                      'sort': 50},
    {'key': 'sla',           ...,                      'sort': 60},
    ...
    # ── 遗留模块 ──
    {'key': 'incidents',     ...,                      'sort': 120},
    {'key': 'changes',       ...,                      'sort': 130},
]
```

**数据库同步：** 使用 Python 脚本直接更新现有 `PageTab` 记录（因为 seed 命令使用 `get_or_create`，不会自动更新已有记录）：

```python
tabs = {
    'service-market': {'sort': 10, 'is_default': True},
    'tickets':        {'sort': 20, 'is_default': False},
    ...
}
for key, vals in tabs.items():
    PageTab.objects.filter(app='itsm', key=key).update(**vals)
```

### 设计决策

- **为什么用 sort 而不是单独的顺序字段？** — 框架已有 `sort` 字段，按整数值排序足够灵活。预留 10 的间隔允许未来插入新 tab。
- **为什么"事件"/"变更"不删除？** — 虽然当前使用频率低，但作为 ITSM 标准模块保留，排序靠后不影响日常使用。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/iam/management/commands/seed_iam_page_configs.py` | 种子数据定义，itsm_tabs 数组重新排序 |
| `docs/guides/frontend-style-guide.md` | 规范更新，新增 #5 tab 左对齐规则 |

## 使用方式

无操作变动。用户进入 ITSM 页面后默认显示"服务市场"tab。Tab 从左到右的排列顺序：
服务市场 → 工单 → 看板 → 流程模板 → 服务目录管理 → SLA → 技能组 → 排班 → 路由 → 升级 → 委托 → 事件 → 变更
