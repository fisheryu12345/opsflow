# OpsFlow — 运维编排平台

> 基于 Django-Vue3-Admin 框架的可视化 Pipeline 编排与执行平台，集成 bamboo-engine 作为流程执行引擎，DeepSeek 作为 AI 生成引擎。

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
│  │  │Pipeline     │  │BambooDjangoRuntime│  │TowerService │  │      │
│  │  │Builder      │  │(ERI 异步)     │  │(launch/poll)│  │      │
│  │  │(bamboo)     │  │(异步)      │  └──────┬──────┘  │      │
│  │  └──────┬──────┘  └──────┬───────┘         │         │      │
│  │         │                │                  │         │      │
│  │  ┌──────┴────────────────┴──────────────────┴──────┐  │      │
│  │  │              Celery Workers                      │  │      │
│  │  │  execute_pipeline + notify_node_status          │  │      │
│  │  └──────────────────────┬──────────────────────────┘  │      │
│  │                         │                              │      │
│  │  ┌──────────────────────┴──────────────────────────┐  │      │
│  │  │      Atom Layer / Executor Factory               │  │      │
│  │  │  ┌─────────┐ ┌──────────┐ ┌──────────────────┐   │  │      │
│  │  │  │Ansible  │ │Http     │ │ESXi/NetApp/Test  │   │  │      │
│  │  │  │(异步) │ │(异步) │ │ServiceNow/Redfish │   │  │      │
│  │  │  └────┬────┘ └─────────┘ └──────────────────┘   │  │      │
│  │  │       │                                        │  │      │
│  │  │  ┌────┴────┐                                   │  │      │
│  │  │  │Ansible  │                                   │  │      │
│  │  │  │Tower    │                                   │  │      │
│  │  │  └─────────┘                                   │  │      │
│  │  └──────────────────────────────────────────────────┘      │
│  │                           │                                 │
│  │  ┌────────────────────────┴─────────────────────────────┐  │
│  │  │                   Data Layer                          │  │
│  │  │  ┌────────────┐ ┌──────────────┐ ┌────────────────┐  │  │
│  │  │  │FlowTemplate│ │FlowExecution │ │OpsLog          │  │  │
│  │  │  │(MySQL)     │ │(MySQL+Redis) │ │(MySQL)         │  │  │
│  │  │  └────────────┘ └──────────────┘ └────────────────┘  │  │
│  │  │  ┌────────────────┐ ┌──────────────┐                 │  │
│  │  │  │OpsKnowledge    │ │AtomRegistry  │                 │  │
│  │  │  │(RAG 知识库)    │ │(meta.json)   │                 │  │
│  │  │  └────────────────┘ └──────────────┘                 │  │
│  │  └──────────────────────────────────────────────────────────┘
└──────────────────────────────────────────────────────────────────┘
```

## 核心功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 可视化画布设计 | ✅ 完成 | X6 Graph 拖拽式编排 |
| AI 自然语言生成 | ✅ 完成 | DeepSeek 根据描述生成 Pipeline |
| 多轮对话修改 | ✅ 完成 | 通过对话逐步完善流程 |
| Pipeline 分析 | ✅ 完成 | AI 分析流程步骤/风险/建议 |
| 自动布局优化 | ✅ 完成 | Sugiyama 分层布局引擎（bk_sops 算法）|
| Diff 对比 | ✅ 完成 | AI 原稿 vs 当前修改对比 |
| 串行执行 | ✅ 完成 | BambooDjangoRuntime 驱动 |
| 条件分支 (Exclusive) | ✅ 完成 | BambooDjangoRuntime.GatewayMixin |
| 并行分支 (Parallel) | ✅ 完成 | BambooDjangoRuntime.GatewayMixin |
| 条件并行 (Conditional) | ✅ 完成 | BambooDjangoRuntime 自动处理 |
| 路径汇聚 (Converge) | ✅ 完成 | BambooDjangoRuntime.ConvergeMixin |
| 暂停/继续 | ✅ 完成 | 执行中暂停，恢复继续 |
| 重试/跳过 | ✅ 完成 | 失败节点重试或跳过 |
| WebSocket 实时监控 | ✅ 完成 | 节点状态 + Tower 作业进度推送 |
| 安全校验 | ✅ 完成 | 白名单/高危/备份检查 |
| 回滚能力 | ✅ 完成 | 原子级别回滚策略 |
| Ansible Tower 集成 | ✅ 完成 | 自适应轮询 + artifacts 提取 |
| 条件表达式增强 | ✅ 完成 | ${node.artifacts.key >= N} 语法 |
| 多平台原子层 | ✅ 完成 | ESXi/NetApp/ServiceNow/Redfish/HTTP |
| 执行入口 UI (运行按钮) | ✅ 完成 | 画布上触发执行 |
| 执行记录页面 | ✅ 完成 | 历史记录列表+详情（含 MonitorCanvas） |
| 审计日志页面 | ✅ 完成 | OpsLog 浏览（风险等级状态点） |
| 知识库管理页面 | ✅ 完成 | OpsKnowledge CRUD（卡片布局） |
| 模板管理页面 | ✅ 完成 | 模板列表/搜索/卡片视图/管道可视化 |
| Dashboard 统计仪表盘 | ✅ 完成 | ECharts 4 图表 + 7 统计卡片 + 用户活动表 |

## 技术栈

| 层 | 技术 |
|---|------|
| 前端框架 | Vue 3 + TypeScript + Vite 4 |
| UI 库 | Element Plus |
| 画布引擎 | AntV X6 (Graph / Stencil / Minimap / History / Clipboard) |
| 后端框架 | Django 4.2 + DRF 3.14 |
| 流程引擎 | bamboo-pipeline 3.29.9 (bamboo-engine 3.0.3) |
| 布局引擎 | Sugiyama 分层图算法（适配 bk_sops drawing_new） |
| AI | DeepSeek (OpenAI-compatible API) |
| 任务队列 | Celery (Redis broker) |
| 数据库 | MySQL + Redis |
| WebSocket | Django Channels |
| 原子执行 | Executor Factory: Ansible Tower / ESXi / NetApp / ServiceNow / Redfish / HTTP / Test |
| Dashboard 后端 | dashboard_stats / dashboard_trend (14 指标 + 30 日趋势) |
