# portal — 模块索引

> 上次自动更新: 2026-06-12

---

## `portal/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Portal app package |
| `apps.py` | Portal — 运维门户/个人工作台 | `PortalConfig` |
| `urls.py` |  | URL configuration for portal app |

## `portal\services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Services package for portal |

## `portal\views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Views package for portal |
| `dashboard.py` | Portal dashboard — aggregate data from all modules | `dashboard_summary()` — 获取门户首页聚合数据<br>`my_tasks()` — 获取我的待办/待审批<br>`quick_stats()` — 快速概览统计<br>`recent_activity()` — 获取近期系统活动 feed<br>`favorites()` — 获取用户的收藏模板/操作<br>`health()` — 系统健康状态 — 各模块基本健康检查 |
