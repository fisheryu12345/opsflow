# OPSflow 功能状态

## 后端已完成功能

| 模块 | 状态 | 说明 |
|---|---|---|
| **Models** | 已完成 | FlowTemplate / TemplateVersion / FlowExecution / ExecutionNode / ExecutionScheme / TemplateNode / TemplateNodeCollect / TemplateCategory / AutoRetryStrategy / NodeTimeoutConfig / NodeExecutionTrace / OpsProject / OpsProjectMembership / SchedulePlan / OpsWebhook / OpsKnowledge / OpsLog / OperationRecord |
| **Flow Engine** | 已完成 | `core/flow_engine.py` — 基于 BambooPipeline 的流程引擎，支持节点分发、上下文传递、子流程调度 |
| **Pipeline Builder** | 已完成 | `core/pipeline_builder/` — 从前端 pipeline_tree JSON 构建 BambooPipeline 活动树 |
| **Signals** | 已完成 | `signals/` — post_set_state 监听器，路由到 state（节点状态持久化）、trace（轨迹记录）、notify（WS推送）、timeout（超时追踪） |
| **Plugins** | 已完成 | 自动发现扫描 + 10 个分组：ansible / common / esxi / http / monitor / netapp / pmax / redfish / servicenow / verify |
| **Views** | 已完成 | Template CRUD + AI 生成/精炼、Execution CRUD + 启动/暂停/取消/重试、SchedulePlan CRUD + 启用/禁用、Plugin CRUD + 表单查询、Log/Knowledge/Project/Webhook/Audit CRUD |
| **Dashboard** | 已完成 | 12 个统计端点：stats / trend / schedule-stats / top-templates / user-activity / status-distribution / node-type-distribution / duration-distribution / node-duration-top / success-rate-trend / template-stats |
| **Schedule** | 已完成 | `core/scheduler_service.py` — 基于 APScheduler 的 Cron 调度，支持自动重试、过期策略 |
| **Webhook** | 已完成 | `core/webhook_service.py` — 流程生命周期事件回调、Node 状态变更回调 |
| **Knowledge** | 已完成 | 知识库 CRUD，模板 - 知识库关联 |
| **API Gateway** | 已完成 | `core/apigw/` — 外部触发执行、查询执行状态、列出模板 |
| **Auto Retry** | 已完成 | 节点失败自动重试，可配置最大次数/间隔 |
| **Timeout** | 已完成 | 节点超时检测 + 强制失败 / 失败并跳过策略 |
| **Safety Guard** | 已完成 | `core/safety_guard.py` — AI 生成的 pipeline 安全性校验（高危命令检查、权限边界） |

## 前端已完成功能

| 模块 | 状态 | 说明 |
|---|---|---|
| **Design Canvas** | 已完成 | X6 Graph + Stencil 拖放 + 连线 + 缩放/平移/适配 + 缩略图 |
| **Stencil** | 已完成 | 分组调色板 + 搜索过滤、子流程专用 Stencil 节点 |
| **Property Panel** | 已完成 | 节点/边属性编辑：参数表单、超时设置、重试配置、条件表达式、输出字段 |
| **Monitor Canvas** | 已完成 | 只读 X6 Graph + WebSocket 实时节点状态着色、进度条 |
| **Pinia Store** | 已完成 | 模式切换、模板/执行数据缓存、项目管理、全局变量、Help Drawer 控制 |
| **AI Integration** | 已完成 | 自然语言生成 pipeline、多轮对话精炼、Diff 对比确认、AI 布局优化、AI 分析 |
| **Dialogs** | 已完成 | CreateTemplateWizard / SubmitWizardDialog / PluginPickerDialog / DryRunDialog / DiffModal / HelpDrawer / ConditionDialog / PluginVisibilityDialog |
| **Pages** | 已完成 | 10 个页面：opsflow / opsflow-template / opsflow-execution / opsflow-approval / opsflow-dashboard / opsflow-log / opsflow-knowledge / opsflow-project / opsflow-webhook / opsflow-stats |
| **Composables** | 已完成 | useGraphCanvas / useDesignCanvas / useMonitor / useGraphValidator / useAutoSave |
| **API Client** | 已完成 | 13 个 API 文件 + 通用 opsflowRequest 实例 + createCrudApi 工厂 |

## Pipeline 格式定义

```json
{
  "nodes": [
    {
      "id": "node_xxx",
      "label": "节点名称",
      "node_type": "start_event|end_event|exclusive_gateway|parallel_gateway|conditional_parallel_gateway|converge_gateway|approval|subprocess|",
      "atom_type": "插件 code（仅 Task 节点）",
      "params": { "key": "value" },
      "x": 100, "y": 200,
      "max_retries": 0,
      "timeout_seconds": null,
      "risk_level": "low|medium|high|critical"
    }
  ],
  "edges": [
    {
      "from": "node_a",
      "to": "node_b",
      "label": "success|failure|条件表达式"
    }
  ]
}
```

### 节点类型

| 类型 | 作用 | 出边规则 |
|---|---|---|
| `start_event` | 流程起点 | 必须正好 1 条出边 |
| `end_event` | 流程终点 | 0 条出边 |
| `exclusive_gateway` | 排他网关 | 每条边包含条件，仅一条满足时通过 |
| `parallel_gateway` | 并行网关 | 所有出边同时执行 |
| `conditional_parallel_gateway` | 条件并行网关 | 满足条件的出边同时执行 |
| `converge_gateway` | 汇聚网关 | 等待所有入边到达后继续 |
| `approval` | 人工审批 | 审批通过走 `success`，拒绝走 `failure` |
| `subprocess` | 子流程 | 引用另一个模板作为子流程执行 |
| （空/原子类型） | Task 节点 | 执行插件原子操作 |

### 边规则

- `label` 为空或 `"success"`：默认成功路径
- `label` 为 `"failure"`：失败路径（gateway 判断条件不满足时）
- 其他字符串：`${source_node.output_field}` 格式的变量条件表达式
- 禁止从 end_event 连出，禁止连向 start_event

## 执行状态机

```
                  ┌──────────┐
                  │ PENDING  │
                  └────┬─────┘
                       │ 用户提交
                       ▼
            ┌──────────────────┐
            │ PENDING_APPROVAL │──── 审批拒绝 ──→ FAILED
            └────────┬─────────┘
                     │ 审批通过
                     ▼
               ┌──────────┐
          ┌───▶│ RUNNING  │◀──── 重试 ────┐
          │    └────┬─────┘               │
          │         │                     │
          │    ┌────▼─────┐         ┌─────┴──────┐
          │    │  PAUSED  │─── 继续 → RUNNING    │
          │    └────┬─────┘         └────────────┘
          │         │ 取消
          │         ▼
          │    ┌──────────┐               ┌──────────┐
          │    │ CANCELLED│               │ FAILED   │
          │    └──────────┘               └────┬─────┘
          │                                    │ 自动重试
          │                                    ▼
          │                              ┌──────────┐
          │                              │ RUNNING  │────→ FINISHED / FAILED
          │                              └──────────┘
          │
          └──── 全部节点完成 ────→ COMPLETED
```

### 状态定义

| 状态 | 含义 | 终态 |
|---|---|---|
| `pending` | 等待执行 | 否 |
| `pending_approval` | 等待人工审批 | 否 |
| `running` | 执行中 | 否 |
| `paused` | 已暂停 | 否 |
| `completed` | 全部节点成功完成 | 是 |
| `failed` | 存在失败节点且无法恢复 | 是 |
| `cancelled` | 用户取消 | 是 |

### 节点级状态流转

```
PENDING → RUNNING / SKIPPED / CANCELLED
RUNNING → FINISHED / FAILED / PAUSED / PENDING_APPROVAL
PAUSED → RUNNING / SKIPPED
PENDING_APPROVAL → FINISHED / FAILED
FAILED → RUNNING（重试）
FINISHED / SKIPPED / CANCELLED → 终态（无合法流转）
BLOCKED → RUNNING
```
