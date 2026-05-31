# OpsFlow — 运维编排平台

> 基于 Django-Vue3-Admin 框架的可视化 Pipeline 编排与执行平台，集成 bamboo-engine 作为流程执行引擎，DeepSeek 作为 AI 生成引擎。适配自 bk_sops 设计理念，面向 AI-First 的运维自动化场景。

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3 + X6)                         │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │Design    │  │Monitor       │  │AI Chat               │      │
│  │Canvas    │  │Canvas        │  │(DeepSeek 交互)       │      │
│  │(X6 Graph)│  │(WebSocket)   │  │                      │      │
│  └────┬─────┘  └──────┬───────┘  └──────────┬───────────┘      │
├───────┼───────────────┼──────────────────────┼──────────────────┤
│  ┌────┴───────────────┴──────────────────────┴──────────┐      │
│  │              API 层 (REST + WebSocket)                │      │
│  │  /api/opsflow/  +  ws/opsflow/execution/{id}/        │      │
│  └────────────────────────┬─────────────────────────────┘      │
│                           │                                     │
│  ┌────────────────────────┴─────────────────────────────┐      │
│  │                   Backend Core                         │      │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  │      │
│  │  │BambooBuilder│  │FlowEngine    │  │TowerService │  │      │
│  │  │(pipeline)   │  │(BambooDjango │  │(launch/poll)│  │      │
│  │  │             │  │ Runtime)     │  └──────┬──────┘  │      │
│  │  └──────┬──────┘  └──────┬───────┘         │         │      │
│  │         │                │                  │         │      │
│  │  ┌──────┴────────────────┴──────────────────┴──────┐  │      │
│  │  │              Celery Workers                      │  │      │
│  │  │  execute_pipeline + notify_node_status          │  │      │
│  │  └──────────────────────┬──────────────────────────┘  │      │
│  │                         │                              │      │
│  │  ┌──────────────────────┴──────────────────────────┐  │      │
│  │  │              Plugin / Atom Layer                  │      │
│  │  │  BasePlugin → PluginService → (9 组 43 原子)    │  │      │
│  │  │  Ansible / ESXi / NetApp / ServiceNow / Redfish  │  │      │
│  │  │  HTTP / Monitor / Common / Pmax                  │  │      │
│  │  └──────────────────────────────────────────────────┘      │
│  │                           │                                 │
│  │  ┌────────────────────────┴─────────────────────────────┐  │
│  │  │                   Data Layer                          │  │
│  │  │  FlowTemplate / FlowExecution / NodeExecutionTrace   │  │
│  │  │  OpsLog / SchedulePlan / OpsKnowledge / PluginMeta   │  │
│  │  │  MySQL + Redis + ERI 表 (bamboo-engine)              │  │
│  │  └──────────────────────────────────────────────────────────┘
└──────────────────────────────────────────────────────────────────┘
```

## 核心功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 可视化画布设计 | ✅ 完成 | X6 Graph 拖拽式编排，9 种自定义节点 |
| AI 自然语言生成 | ✅ 完成 | DeepSeek 根据描述生成 Pipeline |
| 多轮对话修改 | ✅ 完成 | 通过对话逐步完善流程 |
| Pipeline 分析 | ✅ 完成 | AI 分析流程步骤/风险/建议 |
| 自动布局优化 | ✅ 完成 | Sugiyama 分层布局引擎（bk_sops 算法）|
| Diff 对比 | ✅ 完成 | AI 原稿 vs 当前修改对比 |
| 串行/条件/并行/汇聚 | ✅ 完成 | 4 种网关类型，bamboo-engine 驱动 |
| 暂停/继续/重试/跳过 | ✅ 完成 | 节点级控制 + 批量操作 |
| 审批流程 | ✅ 完成 | 审批节点 + 暂停待审 + 通过/拒绝 |
| 子流程 (Embedded/Independent) | ✅ 完成 | 两种模式 + 子流程版本追踪 |
| WebSocket 实时监控 | ✅ 完成 | 节点状态 + Tower 作业进度推送 |
| 安全校验 | ✅ 完成 | 白名单/高危/备份检查/AI 幻觉防御 |
| 回滚能力 | ✅ 完成 | 原子级别回滚策略 |
| 执行轨迹双树 | ✅ 完成 | NodeExecutionTrace + state_tree + 独立日志文件 |
| 变量系统 | ✅ 完成 | 全局变量/引用计数/浏览器/变量提升 |
| 调度计划 | ✅ 完成 | 一次性/CRON 定时触发，APScheduler 集成 |
| Dashboard 仪表盘 | ✅ 完成 | 11 个端点，4 ECharts 图表 + 7 统计卡片 |
| 9 组 43 个标准插件 | ✅ 完成 | Ansible/ESXi/NetApp/ServiceNow/Redfish/HTTP/Monitor/Pmax/Common |
| 视图 Mixin 重构 | ✅ 完成 | 大文件拆分，9 个 Mixin 提取，支持维护 |
| 模块化重构 | ✅ 完成 | signals 包/dashboard 包/validator 提取 |

## 技术栈

| 层 | 技术 |
|---|------|
| 前端框架 | Vue 3 + TypeScript + Vite 4 |
| UI 库 | Element Plus |
| 画布引擎 | AntV X6 2.19 + 8 插件 |
| 后端框架 | Django 4.2 + DRF 3.14 |
| 流程引擎 | bamboo-pipeline 3.29.9 (bamboo-engine 3.0.3) |
| 布局引擎 | Sugiyama 分层图算法（适配 bk_sops drawing_new） |
| AI | DeepSeek (OpenAI-compatible API) + RAG |
| 任务队列 | Celery (Redis broker) |
| 数据库 | MySQL + Redis |
| WebSocket | Django Channels (RedisChannelLayer) |
| 调度器 | APScheduler 3.11 + DjangoJobStore |
| 插件协议 | BasePlugin + Pydantic form_schema |
| 后端代码规模 | ~15,000 行 Python（含插件 2,800 行） |
| 前端代码规模 | ~4,700 行 TypeScript/Vue |
