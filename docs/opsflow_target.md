# OPSflow 平台最终目标与形态

> **版本:** v1.0  
> **最后更新:** 2026-06-07  
> **说明:** 本文档定义 OPSflow 平台的最终目标架构、每个子产品的定位、组件间交互规范，为后续子组件开发提供统一的蓝图参考。

---

## 1. 平台愿景与定位

### 1.1 平台目标

OPSflow 的最终目标是一个 **以流程编排引擎为核心、CMDB 为数据底座、插件化扩展为集成手段的一站式运维自动化平台**。

它既不是蓝鲸套件的重实现，也不是一个简单的 Pipeline 工具，而是：

- **编排驱动** — 一切运维动作最终通过流程引擎编排执行
- **数据内聚** — CMDB 作为内置数据底座，不依赖外部 CMDB 系统
- **可插拔扩展** — 通过 BasePlugin 协议接入任意运维平台
- **AI-First** — DeepSeek 嵌入每一个子产品，自然语言驱动运维操作

### 1.2 核心设计理念

| # | 原则 | 说明 |
|---|------|------|
| 1 | **编排驱动** | 一切运维动作最终通过流程引擎编排执行，非孤立功能。监控告警触发编排、ITSM 变更通过编排实施、AI 对话通过编排执行 |
| 2 | **CMDB 即底座** | CMDB 是唯一的数据真相源，所有子系统依赖 CMDB 获取资源信息，OpsFlow 变量系统深度嵌入 CMDB 查询 |
| 3 | **事件闭环** | 监控告警 → 自动诊断 → 触发流程 → 结果回写，形成自动化闭环，不留"告警了但没人处理"的死角 |
| 4 | **插件化扩展** | 所有执行能力通过 `BasePlugin` 协议集成，任何新平台只需实现 execute/schedule/rollback 即可接入 |
| 5 | **AI-First** | 自然语言驱动操作，DeepSeek 嵌入每一个子产品。不只是"AI 生成流程"，而是"AI 辅助一切运维决策" |

### 1.3 目标用户画像

| 用户角色 | 主要使用 | 使用频率 | 技术能力 |
|---------|---------|---------|---------|
| 运维工程师 | 编排 Pipeline、监控告警、批量作业 | 日常 | Python/Shell/Ansible |
| 配置管理员 | 维护 CMDB 资产、资源关系 | 日常 | 基础 IT 知识 |
| 服务台 | 处理工单、审批变更 | 日常 | 基础 IT 知识 |
| 监控值班 | 处理告警、启动自愈流程 | 轮班 | 运维基础 |
| AI 对话用户 | 自然语言查询资源/执行操作 | 按需 | 不限 |
| 集成开发者 | 开发插件、对接外部系统 | 阶段性 | Python 开发 |
| 平台管理员 | RBAC 权限、项目配置 | 定期 | 系统管理 |

---

## 2. 能力域视图（Capability View）

从用户场景出发，将平台能力组织为 7 大能力域。每个能力域对应一组用户操作场景和技术支撑。

### 2.1 能力域总览

```
┌──────────────────────────────────────────────────────────────────────┐
│                          OPSflow 平台                                │
│                                                                      │
│  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │ ① 编排自动化 │ │ ② 配置管理 │ │ ③ 服务交付 │ │ ④ 监控自愈 │               │
│  │ (opsflow)  │ │ (cmdb)   │ │ (itsm)   │ │ (monitor)│               │
│  └──────┬─────┘ └────┬─────┘ └─────┬────┘ └─────┬────┘               │
│         │             │             │            │                    │
│  ┌──────┴─────┐ ┌────┴──────┐ ┌───┴────────┐ ┌─┴─────────┐           │
│  │ ⑤ 批量作业  │ │ ⑥ AI 辅助  │ │ ⑦ 开放集成  │ │ 系统管理    │           │
│  │(job_plat)  │ │(opsagent) │ │(integ/open)│ │(dvadmin)  │           │
│  └────────────┘ └───────────┘ └────────────┘ └───────────┘           │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 能力域详解

---

#### Domain ①: 流程编排与自动化

**核心价值：** 可视化、可编排、可重复的运维自动化流程定义与执行

| 用户故事 | 用户操作 | 前端组件 | 后端服务 | 数据模型 |
|---------|---------|---------|---------|---------|
| 我要设计一个服务器初始化流程 | 拖拽节点、配置参数、连接成链 | DesignCanvas (X6) | PipelineBuilder | FlowTemplate / TemplateNode |
| 我要选择要执行的插件 | 从调色板拖出插件节点、配置表单 | PluginPicker / PropertyPanel | PluginService / PluginRegistry | PluginMeta |
| 让 AI 帮我生成流程 | 输入自然语言描述、审查生成的 Pipeline | AI Chat 浮窗 / DiffModal | LLMService + RAG | OpsKnowledge |
| 让流程每天凌晨自动执行 | 配置 Cron 表达式、启动调度 | SchedulePlan 管理 | SchedulerService (APScheduler) | SchedulePlan |
| 实时看流程跑到哪了 | 打开监控画布、观察节点着色 | MonitorCanvas (X6+WS) | FlowEngine + Signals | FlowExecution / NodeExecutionTrace |
| 出错了，跳过这个节点继续 | 点击失败节点、选择跳过 | ExecutionDetail | NodeCommandDispatcher | FlowExecution |
| 第三方系统要触发流程 | 调用 API 端点、传入参数 | — | Open API (apigw) | ApiToken |

**涉及子产品:** `opsflow` (主要) + `open_api` (触发入口)

---

#### Domain ②: 配置与资源管理 (CMDB)

**核心价值：** 唯一的 IT 资产数据真相源，为所有子产品提供资源上下文

| 用户故事 | 用户操作 | 前端组件 | 后端服务 | 数据模型 |
|---------|---------|---------|---------|---------|
| 定义服务器模型需要哪些字段 | 模型管理、添加字段类型 | CMDB 模型配置 | ModelService | Neo4j 模型定义 |
| 批量导入新采购的服务器 | Excel 导入 / Agent 自动发现 | 动态表格 | ResourceService | Neo4j 节点 |
| 查看这个应用的依赖拓扑 | 打开拓扑图、浏览关系链 | TopologyCanvas (X6) | GraphService | Neo4j 关系 |
| 在 Pipeline 中引用 CMDB 主机 | 变量选取器、选择资源筛选条件 | VariableBrowser | CmdbVariables | → OpsFlow 变量系统 |
| 主机信息变更了通知我 | 订阅变更事件 | — | cmdb_events (Signal) | → 事件总线 |

**涉及子产品:** `cmdb` (主要) + `opsflow` (变量系统)

---

#### Domain ③: IT 服务交付 (ITSM)

**核心价值：** 标准化 IT 服务请求与变更管理，审批流程与自动化实施无缝衔接

| 用户故事 | 用户操作 | 前端组件 | 后端服务 | 数据模型 |
|---------|---------|---------|---------|---------|
| 申请开通一台新服务器 | 填写工单、选择服务项 | ITSM 工单页 | TicketService | itsm 工单模型 |
| 审批变更申请 | 查看变更详情、通过/拒绝 | 审批面板 | WorkflowService | itsm 审批模型 |
| 变更审批通过后自动实施 | 关联 OpsFlow 模板、配置参数映射 | 变更向导 | → OpsFlow FlowEngine | FlowExecution |
| Pipeline 跑到了审批节点 | 收到审批通知、在线审批 | ExecutionApproval | PluginService (approval) | FlowExecution |

**涉及子产品:** `itsm` (主要) + `opsflow` (审批节点贯通)

---

#### Domain ④: 监控告警与自愈 (Monitor)

**核心价值：** 告警发现 → 通知 → 自愈闭环，减少人工介入

| 用户故事 | 用户操作 | 前端组件 | 后端服务 | 数据模型 |
|---------|---------|---------|---------|---------|
| 查看当前所有告警 | 打开告警仪表盘、按级别筛选 | Monitor Dashboard | AlertManager | monitor 告警模型 |
| 配置磁盘使用率超过 90% 时自动扩容 | 创建自愈策略、关联 OpsFlow 流程 | StrategyWizard | SelfHealingService | monitor 策略模型 |
| 告警触发时自动创建 ITSM 工单 | 配置通知路由规则 | 通知配置 | NotificationService | → ITSM 工单 |
| 自愈流程执行完了，告警自动关闭 | — | — | → monitor 接收 OpsFlow 完成信号 | monitor 告警状态 |

**涉及子产品:** `monitor` (主要) + `opsflow` (自愈流程) + `itsm` (事件工单)

---

#### Domain ⑤: 批量作业执行 (Job Platform)

**核心价值：** 脚本托管、批量分发、文件传输的独立执行平台

| 用户故事 | 用户操作 | 前端组件 | 后端服务 | 数据模型 |
|---------|---------|---------|---------|---------|
| 写一个巡检脚本并管理版本 | 脚本编辑器、版本管理 | Job Script Console | ScriptService | 文件系统 / job 模型 |
| 对 100 台服务器分发脚本并执行 | 选择目标、选择脚本、提交 | Job Execution Panel | ExecutorService / SSH | 执行记录 |
| 传文件到一批主机 | 选择文件、目标路径、分发 | File Transfer UI | TransferService | 文件系统 |
| 查看作业执行结果 | 按执行批次查看结果、下载日志 | Execution History | — | 执行日志 |

**与编排引擎的差异：** OpsFlow 是编排流程（步骤间有条件和依赖），Job Platform 是单次批量执行。两者互补——Job Platform 可作为 OpsFlow 的一个插件原子集成。

**涉及子产品:** `job_platform` (主要) + `agent` (远程执行)

---

#### Domain ⑥: AI 辅助运维 (OpsAgent)

**核心价值：** 自然语言对话式运维，降低操作门槛，加速问题排查

| 用户故事 | 用户操作 | 前端组件 | 后端服务 | 数据模型 |
|---------|---------|---------|---------|---------|
| 查一下生产环境有多少台服务器 | 输入自然语言查询 | Chat 面板 (opsagent) | LLMService → CMDB QueryService | CMDB |
| 帮我执行备份流程 | "帮我备份前端服务器" | Chat 面板 | LLMService → OpsFlow FlowEngine | FlowExecution |
| 分析这个故障根因 | 输入错误信息、查看分析 | Chat 面板 | LLMService + AgentMemory | AgentMemory / OpsKnowledge |
| 上次怎么处理的类似问题 | 问 AI "上次某某问题是怎么解决的" | Chat 面板 | AgentMemory 检索 | AgentMemory |

**涉及子产品:** `opsagent` (主要) + `cmdb` (查询) + `opsflow` (执行) + `knowledge` (RAG)

---

#### Domain ⑦: 开放集成 (Integration + Open API)

**核心价值：** 连接外部系统、暴露平台能力给第三方

| 用户故事 | 用户操作 | 前端组件 | 后端服务 | 数据模型 |
|---------|---------|---------|---------|---------|
| 对接公司内部的监控系统 | 配置连接器、测试连通性 | Connector UI | Integration Hub (连接器管理) | 连接器元数据 |
| 存储外部系统的 API 密钥 | 新增凭据、关联连接器 | Credential Panel | 凭证管理 (加密存储) | 凭证 (加密) |
| 外部 CMDB 想触发 OpsFlow 流程 | 申请 API Token、调用触发执行 | Token 管理 | Open API Gateway | ApiToken |
| 查看外部调用的历史记录 | 查看 API 调用日志 | — | Open API (审计) | OperationRecord |

**涉及子产品:** `integration` (连接管理) + `open_api` (对外暴露)

---

### 2.3 能力域 ↔ 子产品映射速查

| 能力域 | 主要子产品 | 次要子产品/依赖 |
|-------|-----------|---------------|
| ① 编排自动化 | `opsflow` | `open_api`(触发), `itsm`(审批) |
| ② 配置管理 | `cmdb` | `opsflow`(变量), `agent`(自动发现) |
| ③ 服务交付 | `itsm` | `opsflow`(实施), `cmdb`(配置项) |
| ④ 监控自愈 | `monitor` | `opsflow`(自愈流程), `itsm`(事件工单) |
| ⑤ 批量作业 | `job_platform` | `agent`(远程执行), `cmdb`(目标主机) |
| ⑥ AI 辅助 | `opsagent` | `cmdb`, `opsflow`, `knowledge` |
| ⑦ 开放集成 | `integration` + `open_api` | 全部子产品 (提供能力和消费能力) |

---

## 3. 五层架构（Technical View）

### 3.1 架构总览

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  Layer 1: 展现层 (Presentation) — Vue 3 + X6 + ECharts + Element Plus                 │
│  ┌─────────────┐ ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐ │
│  │ OpsFlow     │ │ CMDB      │ │ ITSM     │ │ Monitor   │ │ Job Plat  │ │ OpsAgent │ │
│  │ 画布/监控   │ │ 拓扑/表格  │ │ 工单/审批 │ │ 告警面板   │ │ 作业控制台 │ │ Chat面板 │ │
│  └──────┬──────┘ └─────┬─────┘ └────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬────┘ │
│  ┌──────┴──────┐ ┌─────┴─────┐ ┌────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴────┐ │
│  │ Integration │ │ Portal    │ │ Open API  │ │ 共享设计系统                               │
│  │ 连接器管理   │ │ 首页仪表盘 │ │ 文档页面   │ │ (EChartsWrapper / PageHeader / ...)       │
│  └─────────────┘ └───────────┘ └───────────┘ └────────────────────────────────────────┘ │
│  Pinia Stores (opsflowStore / 各子产品 store) + axios (opsflowRequest)                   │
├───────────────────────────────────────────────────────────────────────────────────────┤
│  Layer 2: API 层                                                                       │
│                                                                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐         │
│  │  内部 REST API (DRF ViewSets):                                                     │
│  │  /api/opsflow/*  /api/cmdb/*  /api/itsm/*  /api/monitor/*  /api/job-platform/*     │
│  │  /api/opsagent/*  /api/integration/*  /api/system/* (dvadmin RBAC)                  │
│  └───────────────────────────────────────────────────────────────────────────┘         │
│                                                                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐         │
│  │  Open API (独立 app: backend/open_api/):                                              │
│  │  /api/open/v1/* — Token认证 + 限流 + 审计 + Webhook                                  │
│  │  端点: 触发执行 / 查询状态 / 列出模板 / 查询CMDB (扩展中)                              │
│  └───────────────────────────────────────────────────────────────────────────┘         │
│                                                                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐         │
│  │  WebSocket (Django Channels + RedisChannelLayer):                                    │
│  │  ws/opsflow/execution/{id}/  ws/opsagent/session/{id}/                              │
│  │  ws/cmdb/topology/  ws/monitor/alert/{id}/ (扩展中)                                  │
│  └───────────────────────────────────────────────────────────────────────────┘         │
├───────────────────────────────────────────────────────────────────────────────────────┤
│  Layer 3: 核心服务层 (Core Services)                                                    │
│                                                                                        │
│  ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌───────────┐ ┌───────────┐  │
│  │ OpsFlow    │ │ CMDB     │ │ ITSM     │ │ Monitor    │ │ Job       │ │ OpsAgent  │  │
│  │ Core       │ │ Core     │ │ Core     │ │ Core       │ │ Platform  │ │ Core      │  │
│  │            │ │          │ │          │ │            │ │ Core      │ │           │  │
│  │ FlowEngine │ │ Model    │ │ Ticket   │ │ AlertMgmt  │ │ ScriptMgr │ │ Session   │  │
│  │ Pipeline   │ │ Graph    │ │ Workflow │ │ SelfHeal   │ │ Executor  │ │ ToolCall  │  │
│  │ Builder    │ │ Query    │ │ Change   │ │ Notify     │ │ Transfer  │ │ Memory    │  │
│  │ Dispatcher │ │          │ │          │ │            │ │           │ │           │  │
│  │ Signals    │ │          │ │          │ │            │ │           │ │           │  │
│  │ Scheduler  │ │          │ │          │ │            │ │           │ │           │  │
│  │ LLMService │ │          │ │          │ │            │ │           │ │           │  │
│  │ Layout     │ │          │ │          │ │            │ │           │ │           │  │
│  └────────────┘ └──────────┘ └──────────┘ └────────────┘ └───────────┘ └───────────┘  │
│                                                                                        │
│  ┌────────────────────────── 集成中心 (Integration Hub) ───────────────────────────┐   │
│  │  连接器管理 | 协议适配 (REST/SOAP/SSH/SNMP) | 凭证管理(加密存储)                     │   │
│  │  数据映射 | 重试/熔断 | 健康检查 | 连接池管理                                       │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │   │
├───────────────────────────────────────────────────────────────────────────────────────┤
│  Layer 4: 执行与插件层 (Execution & Plugin)                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐       │
│  │  Plugin Registry (PLUGIN_REGISTRY) — 自动发现 + BasePlugin 协议              │       │
│  │  12组 51+ 原子插件: ansible/esxi/netapp/redfish/servicenow/http/cmdb/itsm/  │       │
│  │                      monitor/common/pmax/verify                              │       │
│  │  + PluginService 路由 + VariableResolver + SafetyGuard + 生命周期管理        │       │
│  └────────────────────────────────┬────────────────────────────────────────────┘       │
│                                   │                                                     │
│  ┌────────────────────────────────▼────────────────────────────────────────────┐       │
│  │  Agent 执行层                                                                 │       │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │       │
│  │  │ Celery   │ │ Tower    │ │ SSH      │ │ BMC      │ │ Integration Hub  │  │       │
│  │  │ Worker   │ │ Service  │ │ Executor │ │ Redfish  │ │ 连接器 (外部API)  │  │       │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │       │
│  └─────────────────────────────────────────────────────────────────────────────┘       │
├───────────────────────────────────────────────────────────────────────────────────────┤
│  Layer 5: 数据层 (Data Layer)                                                          │
│  ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐    │
│  │ MySQL     │ │ Redis     │ │ Neo4j    │ │ 文件系统    │ │ Vector   │ │ MQ       │    │
│  │ 业务模型    │ │ 缓存/     │ │ CMDB     │ │ 轨迹日志    │ │ DB       │ │ Celery   │    │
│  │ 审计日志    │ │ 超时追踪   │ │ 资源拓扑   │ │ 作业输出    │ │ RAG      │ │ 事件队列  │    │
│  │ dvadmin    │ │ 幂等锁    │ │          │ │ 脚本仓库    │ │ 知识库    │ │          │    │
│  └───────────┘ └───────────┘ └──────────┘ └───────────┘ └──────────┘ └──────────┘    │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 展现层 (Presentation)

每个子产品有独立的前端视图模块，统一基于 Vue 3 + Element Plus。共享设计系统已在 OPSFLOW.md 中定义。

#### 子产品前端分布

| 子产品 | 前端模块路径 | 核心组件 | 可视化依赖 |
|--------|------------|---------|-----------|
| **OpsFlow Core** | `views/apps/opsflow/` | DesignCanvas / MonitorCanvas / PropertyPanel / AI Chat / Dialogs | X6 (核心) |
| **CMDB** | `views/apps/cmdb/` | TopologyCanvas / DynamicTable / ResourceDetail | X6/G6 (拓扑) |
| **ITSM** | `views/apps/itsm/` | TicketList / ApprovalPanel / ChangeCalendar | — |
| **Monitor** | `views/apps/monitor/` | AlertDashboard / StrategyWizard / SelfHealConfig | ECharts |
| **Job Platform** | `views/apps/job-platform/` | ScriptConsole / ExecutionPanel / FileTransfer | — |
| **OpsAgent** | `views/apps/opsagent/` | ChatPanel / ToolCallCard / SessionHistory | — |
| **Integration** | `views/apps/integration/` | ConnectorManager / CredentialPanel / RunMonitor | — |
| **Portal** | `views/apps/portal/` | DashboardHome / QuickEntry / GlobalSearch | ECharts |
| **Open API** | `views/apps/open-api/` | TokenManager / ApiDoc / UsageStats | — |

#### 共享设计系统资产

| 资产 | 位置 | 内容 |
|------|------|------|
| 设计令牌 | `styles/opsflow-variables.scss` | 色板、间距、圆角、阴影、字体 |
| 通用类与混入 | `styles/opsflow-global.scss` | `.of-card`、`.of-fade-in-up`、`of-hover-lift`、`of-hover-shift` |
| 共享组件 | `views/apps/components/` | EChartsWrapper / MetricCard / PageHeader / StatusTag / ValueCell |

#### 展现层交互模式

```
路由 (后端动态路由) → 子产品 index.vue
    → 组件树 (Composables 管理逻辑)
        → API 调用 (axios → DRF REST)
        → WebSocket 实时推送 (Django Channels)
        → Pinia Store 状态管理
```

### 3.3 API 层

#### 内部 API 端点规划

| 前缀 | 子产品 | 当前端点数 | WebSocket |
|------|--------|:---------:|:---------:|
| `/api/opsflow/*` | OpsFlow Core | 30+ | `ws/opsflow/execution/{id}/` |
| `/api/cmdb/*` | CMDB | 8 (Mock) | 规划: `ws/cmdb/topology/` |
| `/api/itsm/*` | ITSM | 基础 | — |
| `/api/monitor/*` | Monitor | 基础 | 规划: `ws/monitor/alert/{id}/` |
| `/api/job-platform/*` | Job Platform | 基础 | — |
| `/api/opsagent/*` | OpsAgent | 基础 | `ws/opsagent/session/{id}/` |
| `/api/integration/*` | Integration Hub | 基础 | — |
| `/api/system/*` | dvadmin RBAC | 完整 | — |

#### Open API（独立 app: `backend/open_api/`）

**定位：** 平台对外的统一 API 出口，独立于 opsflow 核心。已完成从 `opsflow/core/apigw/` 到本 app 的迁移。

**当前实现：**

| 端点 | 方法 | 说明 | 来源 |
|------|------|------|------|
| `POST /api/v2/open/pipelines/trigger/` | 触发 Pipeline 执行 | 提供 template_id 或 pipeline_tree | 从 `opsflow/core/apigw/` 迁入 |
| `GET /api/v2/open/pipelines/{id}/` | 查询执行状态 | 返回状态/node_status/结果 | 从 `opsflow/core/apigw/` 迁入 |
| `GET /api/v2/open/pipelines/templates/` | 列出已发布模板 | 分页返回可用模板 | 从 `opsflow/core/apigw/` 迁入 |
| `POST /api/v2/open/executions/trigger/` | 触发 Job Platform 作业 | 提供 plan_id 或 script_id | 原生 |
| `POST /api/v2/open/cmdb/sync/` | CMDB 资产同步 | 第三方推送资产 | 原生 |
| `POST /api/v2/open/incidents/` | 创建事件工单 | 第三方创建 ITSM 工单 | 原生 |
| `GET /api/v2/open/incidents/{id}/` | 查询工单状态 | 第三方查询 ITSM 工单 | 原生 |
| `GET /api/v2/open/health/` | 健康检查 | 含认证应用信息 | 原生 |

**扩展方向：**

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 跨子产品代理 | 开放 CMDB 查询、ITSM 工单创建等能力 | 高 |
| Token 粒度控制 | 按模板/按操作类型/按资源授权 | 高 |
| 请求签名 | HMAC-SHA256 + 时间戳防重放 | 中 |
| 限流增强 | 按 Token 级别配额管理 | 中 |
| 文档自动生成 | drf-spectacular / Swagger 集成 | 中 |
| Webhook 回调 | 外部系统可以注册回调接收事件通知 | 低 |

**注意：** Open API 不使用 `DetailResponse`/`ErrorResponse` 格式，**保持独立 API 规范**（RESTful 标准 JSON），不强制 `code` 字段。

#### WebSocket 通道

| 通道路径 | 用途 | 所属子产品 | 状态 |
|---------|------|-----------|:----:|
| `ws/opsflow/execution/{id}/` | Pipeline 执行实时监控 | OpsFlow Core | ✅ 完成 |
| `ws/opsagent/session/{id}/` | AI 对话流式响应 | OpsAgent | ✅ 完成 |
| `ws/cmdb/topology/` | 拓扑图实时协作 | CMDB | 规划 |
| `ws/monitor/alert/{id}/` | 告警实时推送 | Monitor | 规划 |

#### 统一 API 规范

**所有内部 API 必须遵守：**

| 场景 | 响应类 | code | 说明 |
|------|--------|:----:|------|
| 成功（单条） | `DetailResponse(data)` | 2000 | 非分页列表也用此 |
| 成功（分页） | `get_paginated_response()` / `SuccessResponse()` | 2000 | 必须包含 total |
| 业务错误 | `ErrorResponse(msg, code=4000)` | 4000 | 不可用裸 Response() |
| 校验错误 | `ErrorResponse(msg, code=4000)` | 4000 | — |
| 权限错误 | DRF PermissionDenied | 401 | — |
| 请求错误 | DRF ValidationError | 400 | — |

**禁止：** 裸 `Response()`、无 `code` 字段的响应、非标准分页格式。

### 3.4 核心服务层

#### 子产品定位与核心模块

---

##### OpsFlow Core — 编排引擎（成熟度 5/5）

**定位：** 整个平台的核心，所有运维自动化流程的编排与执行中枢

| 模块 | 职责 | 当前状态 |
|------|------|:--------:|
| `FlowEngine` | 流程执行主入口 (start/pause/resume/cancel/retry/skip) | ✅ 完整 |
| `PipelineBuilder` | 前端 pipeline_tree → bamboo-engine DAG | ✅ 完整 |
| `PluginService` | 原子执行路由 (execute/schedule/rollback) | ✅ 完整 |
| `NodeCommandDispatcher` | 节点级操作 + 轨迹追踪 | ✅ 完整 |
| `Signals` (handlers) | 状态变更异步处理 (state/trace/notify/timeout) | ✅ 完整 |
| `SafetyGuard` | Pipeline 安全校验 | ✅ 完整 |
| `SchedulerService` | APScheduler 定时调度 | ✅ 完整 |
| `LLMService` | DeepSeek AI 生成/精炼/分析 | ✅ 完整 |
| `VariableResolver` | ${key} 变量运行时解析 + Mako | ✅ 完整 |
| `LayoutEngine` | Sugiyama 分层图自动布局 (18 文件) | ✅ 完整 |
| `apigw/` (已迁移) | 外部 API (已迁移到 `open_api` app，目录已删除) | ✅ 已迁移 |

---

##### CMDB — 配置管理数据库（成熟度 4/5）

**定位：** 唯一的数据真相源，为所有子产品提供资产、拓扑、资源关系。正在从 MySQL 模型向 Neo4j 图数据库重构。

| 模块 | 职责 | 当前状态 |
|------|------|:--------:|
| 模型管理 | 资源模型定义（服务器/网络/存储/中间件/应用） | 🔄 重构中 |
| 拓扑引擎 | 资产间关系的图查询与可视化 | 🔄 重构中 |
| 资源查询 | 资源筛选/搜索/详情 | ✅ Mock 数据 8 组 |
| CMDB 变量 | OpsFlow 变量系统集成 (cmdb_variables.py) | ✅ 基础 |
| 变更追踪 | 资源变更历史记录 | 📅 规划 |
| 自动发现 | Agent 上报 + 轮询扫描自动更新 | 📅 规划 |

---

##### ITSM — IT 服务管理（成熟度 4/5）

**定位：** 事件管理、变更管理、审批流程。审批节点与 OpsFlow 深度集成，工单可触发编排流程。

| 模块 | 职责 | 当前状态 |
|------|------|:--------:|
| 工单管理 | 事件/服务请求/变更工单创建流转 | ✅ 基础 |
| 审批流 | 多级审批 + 会签 + 知会 | ✅ 基础 |
| 变更管理 | 变更申请/评估/审批/实施/回顾 | ✅ 基础 |
| 服务目录 | 定义可请求的 IT 服务项 | 📅 规划 |
| OpsFlow 集成 | 审批节点贯通 + 变更自动实施 | 🔄 完善中 |

---

##### Monitor — 监控告警与自愈（成熟度 4/5）

**定位：** 告警检测 + 通知分发 + 自愈触发。复用外部监控系统（Prometheus），专注于告警聚合、通知路由、自愈闭环。

| 模块 | 职责 | 当前状态 |
|------|------|:--------:|
| AlertManager | 多源告警接入 → 去重 → 聚合 → 路由 | ✅ 基础 |
| Notification | 通知渠道 (钉钉/企微/邮件/短信) + 升级策略 | ✅ 基础 |
| SelfHealing | 告警 → 匹配策略 → 触发 OpsFlow 流程 | 🔄 完善中 |
| Strategy | 自愈策略配置 (条件 + 动作 + 生效时间) | ✅ 基础 |
| 自愈闭环 | 流程完成 → 更新告警状态 | 📅 规划 |

---

##### Job Platform — 批量作业平台（成熟度 3/5）

**定位：** 脚本托管、批量分发、文件传输。与 OpsFlow 互补——OpsFlow 负责编排流程，Job Platform 负责单次批量执行。

| 模块 | 职责 | 当前状态 |
|------|------|:--------:|
| 脚本管理 | 脚本版本管理/语法检查/参数定义 | ✅ 基础 |
| 作业执行 | 脚本分发 → 目标执行 → 结果收集 | 🔄 完善中 |
| 文件分发 | 源 → 目标文件传输 | 🔄 完善中 |
| 执行账户 | SSH Key/密码管理，执行身份控制 | 📅 规划 |

---

##### OpsAgent — AI 运维助手（成熟度 3/5）

**定位：** 基于 DeepSeek 的对话式运维界面，自然语言 → 工具调用 → 操作执行。

| 模块 | 职责 | 当前状态 |
|------|------|:--------:|
| `Session` | 对话会话管理 (上下文/历史/状态) | ✅ 基础 |
| `AgentMemory` | 持久化经验记忆 (故障模式/操作经验) | ✅ 基础 |
| `ToolRegistry` | 工具注册: 查询 CMDB / 触发 OpsFlow / 查看监控 | 🔄 完善中 |
| `AuditRecord` | 风险评估 (操作 × 环境 × 影响半径) | ✅ 基础 |
| 多轮操作 | 通过对话完成复杂多步运维操作 | 📅 规划 |

---

##### Integration Hub — 集成中心（成熟度 3/5）

**定位：** 横向基础设施层，所有子产品的外部系统连接管理统一入口。

| 模块 | 职责 | 当前状态 |
|------|------|:--------:|
| 连接器管理 | 连接器注册/配置/版本管理 | ✅ 基础 |
| 协议适配 | REST / SOAP / SSH / SNMP / JDBC / gRPC 统一抽象 | 🔄 完善中 |
| 凭证管理 | 加密存储 + 自动注入 | 📅 规划 |
| 运行监控 | 连接健康检查 + 调用统计 + 熔断/重试 | 📅 规划 |

**被谁依赖：** 几乎所有子产品——OpsFlow 插件执行需要外部 API 连接，CMDB 需要连接设备，Monitor 需要连接 Prometheus，Job Platform 需要 SSH 连接到目标主机。

---

##### Agent — 远程 Agent（成熟度 2/5）

**定位：** 运行在目标主机上的 Agent 程序，负责命令执行、数据采集、心跳上报。

| 模块 | 职责 | 当前状态 |
|------|------|:--------:|
| Agent 注册 | Agent → Server 注册和认证 | 📅 规划 |
| 命令执行 | 接收 Server 指令 → 执行 → 返回结果 | 📅 规划 |
| 数据采集 | 主机信息/进程/日志采集上报 | 📅 规划 |
| 心跳保活 | 定期心跳 + 离线检测 | 📅 规划 |

---

#### 子产品间服务调用矩阵

**调用规范（单体架构期）：** 子产品之间通过**直接 Python 函数调用**。被调用方以 `services/` 模块暴露清晰的接口，调用方 `from cmdb.services import xxx` 导入使用。异步解耦场景使用 Django Signal 或 Celery 任务。

| 调用方 \ 被调用方 | OpsFlow | CMDB | ITSM | Monitor | JobPlat | OpsAgent | IntegHub |
|-----------------|:-------:|:----:|:----:|:------:|:-------:|:--------:|:--------:|
| **OpsFlow** | — | 🔗 变量查询主机 | 🔗 审批节点贯通 | — | 🔗 Tower 作业 | — | 🔗 插件调用外部API |
| **CMDB** | — | — | — | — | 🔗 自动发现脚本 | — | 🔗 设备连接 |
| **ITSM** | 🔗 变更实施流程 | 🔗 查询配置项 | — | — | — | — | 🔗 通知发送 |
| **Monitor** | 🔗 触发自愈流程 | 🔗 查询告警对象 | 🔗 创建事件工单 | — | — | — | 🔗 发送告警通知 |
| **JobPlat** | — | 🔗 查询目标主机 | — | — | — | — | 🔗 SSH 连接池 |
| **OpsAgent** | 🔗 创建/查询执行 | 🔗 查询资源 | 🔗 查询/创建工单 | 🔗 查询告警 | — | — | — |
| **Integration** | — | — | — | — | — | — | — |

> 🔗 = 直接 Python 调用

**信号/事件驱动场景（异步解耦）：**

| 事件 | 发送方 | 接收方 | 动作 |
|------|--------|--------|------|
| `pipeline.completed` | OpsFlow (signals) | Monitor | 关闭关联告警 |
| `pipeline.failed` | OpsFlow (signals) | Monitor / ITSM | 升级告警 / 创建事件工单 |
| `cmdb.resource.changed` | CMDB | ITSM / OpsAgent | 触发重新认证 / 通知 AI |
| `monitor.alert.triggered` | Monitor | SelfHealing / OpsAgent / ITSM | 触发自愈 / 通知 AI / 创建工单 |

### 3.5 执行与插件层

#### Plugin Registry

```python
# 结构
PLUGIN_REGISTRY: Dict[str, Dict[str, Type[BasePlugin]]]  # {code: {version: class}}
PLUGIN_GROUP_MAP: Dict[str, List[str]]                   # {group: [code, ...]}
```

**当前插件组（12 组，51+ 原子）：**

| 分组 | 插件数 | 示例 | 风险等级 |
|------|:------:|------|:--------:|
| `ansible` | 9+ | shell, file_copy, java_deploy, docker_deploy | medium~high |
| `cmdb` | 2 | query, resource_selector | low |
| `common` | 2 | send_alert, test_print_time | low~medium |
| `esxi` | 5 | create_vm, power_on/off, destroy_vm | high |
| `http` | 1 | api_call | low |
| `itsm` | 2 | create_ticket, update_ticket | low |
| `monitor` | 3 | disk_check, health_check, ping_test | low |
| `netapp` | 5 | create_volume, create_snapshot, delete_volume | high |
| `pmax` | 3 | storage_group, snapshot, performance | high |
| `redfish` | 7 | power_cycle, firmware_inventory, set_boot_device | high |
| `servicenow` | 5 | create_incident, create_change_request, get_cmdb_ci | low |
| `verify` | 1 | ip_ops_verify | low |

#### PluginService 路由

```
PluginService.execute(data, parent_data)
  ├── 提取 _atom_type / 参数
  ├── 特殊原子: subprocess_independent → 独立子流程
  ├── get_plugin(atom_type) → PLUGIN_REGISTRY 查找
  ├── resolve_params() → ${key} 变量替换
  ├── plugin_instance.execute(**params)
  │     ├── 同步 → 直接返回结果
  │     └── 异步 → schedule() 轮询 (适用于 Tower/Redfish 等)
  ├── rollback() → 失败时回滚
  └── _promote_result() → _result 提升到上下文 (供条件网关评估)
```

#### Agent 执行层

| 执行通道 | 适用场景 | 集成方式 |
|---------|---------|---------|
| **Celery Worker** | 内置 Python 执行 (测试/查询/告警) | `er_execute` 队列 |
| **Tower Service** | Ansible Tower/AWX 作业 | REST API + 轮询 |
| **SSH Executor** | 远程主机脚本执行 | paramiko |
| **Redfish** | BMC 服务器管理 | Redfish REST API |
| **ESXi** | VMware vCenter 操作 | pyVmomi / REST API |
| **Integration Hub** | 第三方 REST/SOAP 插件 | 连接器管理 |

#### 插件扩展方向

| 方向 | 说明 | 优先级 |
|------|------|:------:|
| 插件市场 | 插件包打包/上传/安装机制 | 低 |
| 完整 EsxiExecutor | 替换伪代码为真实 pyVmomi 调用 | 高 |
| 完整 NetAppExecutor | 替换伪代码为 ONTAP REST API | 高 |
| 完整 ServiceNowExecutor | 替换骨架为真实实例调用 | 中 |
| 完整 RedfishExecutor | 替换骨架为真实 BMC 调用 | 中 |
| 统一凭证管理 | Vault / django-fernet-fields 加密存储 | 高 |
| 幂等保障 | 标注每个插件的幂等性，高危操作二次确认 | 中 |
| 异步执行统一 | 长耗时操作异步化，统一 schedule 模式 | 中 |

### 3.6 数据层

#### 存储分布

| 存储引擎 | 用途 | 对应子产品 |
|---------|------|-----------|
| **MySQL** (utf8mb3) | 所有业务模型、审计日志、RBAC、调度计划、项目配置 | 全部 |
| **Redis** | 缓存 / 节点超时追踪 (Sorted Set) / 幂等锁 / Celery Broker | 全部 |
| **Neo4j** | CMDB 图数据 — 资源节点、关系、拓扑 | CMDB |
| **文件系统** | 节点轨迹日志 (JSON Lines) / Tower 作业输出 / 脚本仓库 | OpsFlow / Job Platform |
| **Vector DB** | OpsKnowledge 向量嵌入 + RAG 检索 | OpsAgent / OpsFlow |
| **MQ (Celery)** | 任务队列 (er_execute / er_schedule / default) | 全部 (Celery 任务) |

#### 表命名规范

```
ops_<子产品前缀>_<表名>
```

| 前缀 | 子产品 | 示例 |
|------|--------|------|
| `ops_flow_` | OpsFlow Core | `ops_flow_template`, `ops_flow_execution` |
| `ops_template_` | OpsFlow (模板相关) | `ops_template_version`, `ops_template_node` |
| `ops_` | OpsFlow (其他) | `ops_plugin_meta`, `ops_project` |
| `cmdb_` | CMDB | 规划中 |
| `itsm_` | ITSM | 已有 |
| `mon_` / `monitor_` | Monitor | 已有 |
| `job_` | Job Platform | 规划中 |
| `opsagent_` | OpsAgent | 已有 |
| `integ_` | Integration Hub | 规划中 |
| `oper_` | 审计/操作记录 | `ops_operation_record`, `ops_log` |
| `webhook_` | Webhook | `ops_webhook_config`, `ops_webhook_log` |

**跨产品外键：** 尽量避免，必要时只通过主键 ID 引用。非核心关联由服务层代码逻辑管理，而非数据库外键。

**特殊约束：** MySQL utf8mb3 不支持 4 字节 Unicode（emoji），所有写入操作必须过滤或替换 emoji 字符。

---

## 4. 跨组件交互规范

### 4.1 直接调用（主模式）

**适用范围：** 单体架构期所有跨子产品的同步调用。

**调用方式：**

```python
# 被调用方 — 在 services/ 中暴露清晰的接口
# backend/cmdb/services/host_query.py
class CmdbHostQuery:
    @staticmethod
    def query_by_ip(ip: str, project_id: int) -> dict | None:
        ...

# 调用方 — 直接 import 使用
# backend/opsflow/services/variable_service.py
from cmdb.services.host_query import CmdbHostQuery

def resolve_host_variable(ip: str, project_id: int):
    host = CmdbHostQuery.query_by_ip(ip, project_id)
    return host
```

**守则：**
- 被调用方必须暴露**稳定的函数签名**（参数类型、返回值类型明确）
- 调用方不能绕过 services 层直接访问被调用方的 models/views
- 被调用方修改内部实现不影响调用方（封装原则）
- 无循环依赖（A → B → C → A 禁止）

### 4.2 事件驱动（异步解耦）

**适用范围：** 不需要同步返回的跨子产品通知。

**基于 Django Signal（单进程内异步）：**

```python
# backend/opsflow/signals/events.py — 定义事件
class OpsflowEvents:
    PIPELINE_COMPLETED = 'pipeline.completed'
    PIPELINE_FAILED = 'pipeline.failed'

# backend/monitor/signals/handlers.py — 订阅
from django.dispatch import receiver
from opsflow.signals.events import OpsflowEvents

@receiver(OpsflowEvents.PIPELINE_COMPLETED)
def close_related_alerts(sender, execution_id, **kwargs):
    # 查询关联告警并关闭
    ...
```

**基于 Celery 任务（跨进程异步）：**

```python
# backend/opsflow/tasks.py
@shared_task(queue='default')
def notify_monitor_pipeline_completed(execution_id, result):
    """OpsFlow 完成后通知 Monitor"""
    ...

# 在信号处理器中调用
notify_monitor_pipeline_completed.delay(execution.id, result)
```

### 4.3 对外暴露（Open API）

**适用范围：** 外部第三方系统通过 API 调用平台能力。

**认证流程：**

```
外部系统 → 申请 API Token (通过 OPEN API 管理界面)
         → 在请求 Header 中携带 Authorization: Token xxxxxx
         → Open API 验证 Token 有效性和权限
         → 转发请求到对应子产品的内部服务
         → 返回标准化响应 + 记录审计日志
         → 可选: 注册 Webhook 回调接收事件通知
```

**Open API 作为独立 app (backend/open_api/)，不绑定于 opsflow core。** 当前 `opsflow/core/apigw/` 的 apigw endpoints 将迁移至此。

---

## 5. 各子产品当前状态与路线图

### 5.1 成熟度矩阵

| 子产品 | 成熟度 | 核心引擎 | 前端页面 | API 端点 | 测试覆盖 | 文档 |
|-------|:------:|:--------:|:--------:|:--------:|:--------:|:----:|
| **OpsFlow Core** | ⭐⭐⭐⭐⭐ | ✅ 完整 | ✅ 21 组件 | ✅ 30+ | ✅ 基础 | ✅ 完整 |
| **dvadmin (RBAC)** | ⭐⭐⭐⭐⭐ | ✅ 完整 | ✅ 完整 | ✅ 完整 | — | ✅ |
| **CMDB** | ⭐⭐⭐⭐☆ | 🔄 Neo4j 重构 | ✅ 拓扑+表格 | ⚠️ Mock 8组 | — | 🔄 |
| **ITSM** | ⭐⭐⭐⭐☆ | ✅ 基础 | ✅ 完成 | ✅ 基础 | — | 🔄 |
| **Monitor** | ⭐⭐⭐⭐☆ | ✅ 基础 | ✅ 完成 | ✅ 基础 | — | 🔄 |
| **Open API** | ⭐⭐⭐⭐☆ | ✅ Token+限流 | ✅ 基础 | ✅ 基础 | — | 🔄 |
| **Portal** | ⭐⭐⭐⭐☆ | — | ✅ 完成 | — | — | — |
| **Integration Hub** | ⭐⭐⭐☆☆ | ✅ 基础 | ✅ 基础 | ✅ 基础 | — | 🔄 |
| **Job Platform** | ⭐⭐⭐☆☆ | 🔄 完善中 | ✅ 基础 | ✅ 基础 | — | 🔄 |
| **OpsAgent** | ⭐⭐⭐☆☆ | 🔄 完善中 | ✅ 基础 | ✅ 基础 | — | 🔄 |
| **Agent (远程)** | ⭐⭐☆☆☆ | 📅 规划 | — | — | — | — |
| **CI/CD + K8s** | ⭐☆☆☆☆ | 📅 规划 | — | — | — | — |

### 5.2 路线图 TODO

#### P0 — 高优先级（当前迭代）

- [x] **Open API 独立化** — 将 `opsflow/core/apigw/` 功能迁移到 `backend/open_api/`，使其成为跨子产品的统一对外出口
- [ ] **CMDB Neo4j 重构** — 完成模型驱动架构，替换 Mock 数据为真实 Neo4j 查询
- [ ] **集成中心凭证管理** — 实现统一加密存储 (Vault / django-fernet-fields)，消除各子产品自身管理密码
- [ ] **完整 EsxiExecutor** — 替换伪代码为真实 pyVmomi 调用 (create_vm/destroy_vm 等)
- [ ] **完整 NetAppExecutor** — 替换伪代码为 ONTAP REST API 调用
- [ ] **Monitor 自愈闭环** — 自愈流程完成后自动更新告警状态，信号驱动

#### P1 — 中优先级

- [ ] **项目级 RBAC 增强** — viewer 只读权限强制 + 跨项目模板共享管理界面
- [ ] **操作审计前端** — OperationRecord 浏览/过滤/导出页面
- [ ] **ITSM OpsFlow 审批深度集成** — OpsFlow 审批节点与 ITSM 工单系统双向贯通
- [ ] **OpsAgent 工具链完善** — 更多 Tool: CMDB 查询/ITSM 工单/Monitor 告警
- [ ] **TemplateNode/ExecutionNode 节点同步定时任务** — 确保 pipeline_tree 和节点持久化行记录一致性
- [ ] **Dry Run 增强** — 执行结束支持一键清理测试数据
- [ ] **模板自动保存冲突提示** — 多人编辑时冲突检测前端集成

#### P2 — 低优先级

- [ ] **Job Platform SSH 执行器完善** — 连接池 + 密钥管理 + 批量分发
- [ ] **Agent 远程程序** — Agent 注册/心跳/命令下发/数据采集
- [ ] **插件市场** — 插件打包/上传/安装/版本管理机制
- [ ] **配置驱动表单架构** — 参考 bk-sops 的 JSON Schema 表单架构，替代当前手写表单
- [ ] **CI/CD + K8s 部署支持** — Helm Chart / Operator / GitOps 集成
- [ ] **批量删除模板/执行** — 前端批量选择 + 后端批量删除端点
- [ ] **Tower Webhook 回调方案** — 替代轮询，减少 Tower API 压力

---

## 6. 开发指引

### 6.1 新子组件开发五问

在开发一个新子组件（功能模块）前，先回答这五个问题：

1. **在哪层？** 这个组件属于五层架构中的哪一层？它的上下游接口是谁？
2. **用户场景？** 用户在什么情况下使用它？对应哪个能力域？
3. **依赖谁？** 需要调用其他子产品的哪些服务？调用方式是什么（直接调用 / 信号 / Celery）？
4. **被谁依赖？** 其他子产品会调用我吗？我需要暴露什么接口？
5. **数据在哪？** 数据存储在哪（MySQL / Redis / Neo4j / 文件系统）？表名前缀是什么？

### 6.2 目录结构模板

**后端子产品标准结构：**

```
backend/<app_name>/
├── models/           # 数据模型（多文件包）
├── views/            # API 视图 (ViewSets)
├── services/         # 业务逻辑层（跨产品调用入口）
├── signals/          # 信号处理（可选）
├── tests/            # 测试
├── management/       # Django 管理命令（可选）
├── migrations/
├── serializers.py
├── urls.py
└── apps.py
```

**前端子产品标准结构：**

```
web/src/views/apps/<app-name>/
├── index.vue                 # 主页面
├── api/                      # API 客户端
├── stores/                   # Pinia Store（可选）
├── components/               # 子组件
├── composables/              # 组合函数（可选）
├── types/                    # TypeScript 类型定义（可选）
```

### 6.3 关键规范速查

| 规范 | 要求 | 参考文件 |
|------|------|---------|
| API 响应格式 | `DetailResponse` / `SuccessResponse` / `ErrorResponse` | CLAUDE.md (API Response Convention) |
| 日志 | `import logging; logger = logging.getLogger(__name__)` | CLAUDE.md (Logging Convention) |
| 前端样式 | SCSS scoped, `$of-*` 变量, `.of-card` 类 | OPSFLOW.md |
| 无 emoji | 所有 MySQL 存储路径过滤 4 字节 Unicode | CLAUDE.md, OPSFLOW.md |
| 代码语言 | 英文代码 + 双语注释 | CLAUDE.md |

### 6.4 开发流程参考

```
设计新功能
  → 确认在 docs/opsflow_target.md 对应的层和能力域
  → 确认跨产品调用关系（直接调用/信号）
  → 确认存储位置和表名
  → 开发后端 (Models → Services → Views → URLs)
  → 开发前端 (API → Store → Components → Page)
  → 测试并更新架构文档
```

---

## 7. 附录：术语表

| 术语 | 全称 | 说明 |
|------|------|------|
| Pipeline | — | 由节点和边组成的 DAG 流程定义 |
| 节点 (Node) | — | Pipeline 中的步骤单元（原子/网关/审批/子流程） |
| 边 (Edge) | — | 节点间的连接，可带条件标签 |
| 网关 (Gateway) | — | 控制流程分支/汇聚的特殊节点 |
| 原子 (Atom) | — | 最小执行单元（插件的具体操作） |
| Plugin | — | 实现 BasePlugin 协议的原子插件 |
| FlowTemplate | — | Pipeline 的模板定义（可发布版本） |
| FlowExecution | — | FlowTemplate 的一次执行实例 |
| bamboo-engine | — | 底层流程执行引擎 DAG 遍历器 |
| BambooDjangoRuntime | — | bamboo-engine 的 Django ORM 运行时 |
| ERI | — | Engine Runtime Interface，bamboo-engine 的运行时数据 |
| Sugiyama | — | 分层图自动布局算法 |
| APScheduler | — | Python 定时任务调度库 |
| RAG | — | Retrieval-Augmented Generation，检索增强生成 |
| BasePlugin | — | 插件基类协议 (execute/schedule/rollback/get_form_config) |
| Stencil | — | X6 画布的拖拽节点调色板 |
| Dry Run | — | 使用 test 原子替换后的安全执行预览模式 |
| Integration Hub | — | 集成中心，连接器管理和协议适配的统一入口 |
