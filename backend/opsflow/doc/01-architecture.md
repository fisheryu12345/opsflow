# 系统架构设计

## 整体架构

OpsFlow 采用**前后端分离 + 异步任务 + WebSocket 推送 + 多平台原子层**的架构。

```
┌───────────────┐     REST API      ┌──────────────────┐     Celery      ┌──────────────────┐
│   Vue 3 X6    │ ◄──────────────►  │  Django Backend  │ ◄─────────────► │    Worker        │
│   Design      │                   │                  │                 │                  │
│   Canvas      │ ◄─── WebSocket ──► │  Channels        │                 │  BambooDjango    │
│               │  (状态实时推送)    │  Consumer        │                 │  Runtime         │
│   Monitor     │                   └──────────────────┘                 │  (eri/exec/sched)│
│   Canvas      │                         │                              └──────────────────┘
└───────────────┘                         │                                    │
                                          ▼                                    ▼
                                   ┌──────────────┐                 ┌──────────────────┐
                                   │    Redis     │                 │     MySQL        │
                                   │  (Celery 消  │                 │  ERI 表 (11张)   │
                                   │   息队列)    │                 │  ComponentModel   │
                                   └──────────────┘                 └──────────────────┘
```

## 分层设计

### 1. 前端展示层

- **DesignCanvas**: X6 Graph 画布，支持拖拽式编排，含 Stencil（组件面板）、Minimap（小地图）、PropertyPanel（属性面板）
- **MonitorCanvas**: 只读画布，通过 WebSocket 接收节点状态并实时着色（含 Tower 作业进度）
- **AI Chat**: 浮窗式对话界面，支持多轮交互生成/修改 Pipeline
- **DiffModal**: 对比 AI 原始生成和当前修改

### 2. API 层

- RESTful API (`/api/opsflow/*`): 模板 CRUD、执行 CRUD、日志、知识库
- WebSocket (`ws/opsflow/execution/{id}/`): 实时推送节点状态 + Tower 作业状态
- Action 端点: `start/pause/resume/retry/skip`、`create_from_ai/refine/analyze/ai_layout`

### 3. 核心引擎层

- **build_bamboo_pipeline()**: 将前端自定义格式转换为 bamboo-engine 标准 Pipeline Tree
- **FlowEngine**: 流程执行引擎，使用 BambooDjangoRuntime + api.run_pipeline() 驱动执行
- **AnsibleAtomService**: 实现 bamboo-engine Service 接口，桥接原子执行
- **signals.py**: post_set_state 信号处理器，异步追踪节点状态变化并更新 FlowExecution
- **TowerService**: Ansible Tower (AWX) REST API 封装（触发/轮询/结果提取）

### 4. 原子层

- **AtomRegistry**: 从 `ansible_atoms/atoms/*/meta.json` 加载原子元数据（含 executor_type 字段）
- **Executor Factory**: 根据 executor_type 自动分发到对应执行器（Ansible/ESXi/NetApp/ServiceNow/Redfish/HTTP/Test）
- **Atomic Executor**: 各平台执行器实现统一 `execute()/rollback()` 接口

### 5. 数据层

- **MySQL**: FlowTemplate、FlowExecution、OpsLog、OpsKnowledge、ERI 状态表（11 张）、ComponentModel
- **Redis**: Celery 消息队列、Tower 并发信号量

## 执行流程

### 完整 Pipeline 执行时序

```
用户点击"执行"
    │
    ▼
POST /api/opsflow/executions/{id}/start/
    │
    ▼
FlowEngine.start()
    │ 写入 execution.status = "running"
    │ execution.started_at = now()
    ▼
execute_pipeline_task.delay(execution_id)  ← Celery 异步
    │
    ▼
FlowEngine.run()
    │
    ├─ build_bamboo_pipeline(template)  → Pipeline Tree dict
    ├─ 保存 bamboo_pipeline_id 到 context
    │
    └─ api.run_pipeline(runtime=BambooDjangoRuntime(), pipeline=pipeline)
         │
         │  BambooDjangoRuntime 内部驱动执行:
         │  ├─ ProcessMixin → 创建 Process/Node 记录
         │  ├─ TaskMixin   → 调度到 Celery er_execute/er_schedule 队列
         │  ├─ StateMixin  → 状态机转换 + 发送 post_set_state 信号
         │  ├─ ActivityMixin → 查找 Service → AnsibleAtomService.execute()
         │  │
         │  │  每个 activity 执行:
         │  │    1. BambooDjangoRuntime.get_service(code) → AnsibleAtomService
         │  │    2. → AtomExecutorFactory → AnsibleExecutor
         │  │    3.   → TowerService.launch_job()  POST /launch/
         │  │    4.   → TowerService.poll_job()    自适应轮询
         │  │    5.   → TowerService.extract_result() artifacts
         │  │    6. 成功 → FINISHED / 失败 → FAILED
         │  │
         │  ├─ GatewayMixin → ExclusiveGateway / ParallelGateway / ConvergeGateway
         │  └─ 完成 → 根节点 FINISHED
         │
         └─ run_pipeline 异步返回（实际执行在 Celery 队列中）

节点状态变更（异步，通过信号）:
    │
    ▼
post_set_state 信号 (pipeline.eri.signals)
    │
    ├─ node_id == root_id:
    │     FINISHED  → execution.status = "completed"
    │     FAILED    → execution.status = "failed"
    │     SUSPENDED → execution.status = "paused"
    │     RUNNING   → execution.status = "running"
    │     _notify_completed() → WS group_send
    │
    └─ 子节点 FINISHED/FAILED:
          _log_node_result() → 从 ERI Data 读取 outputs → OpsLog
          _notify_node_status() → WS 推送节点状态
```

### Tower 交互子流程

```
AnsibleExecutor.execute()
  │
  ├─ TowerService.launch_job()
  │    ├─ POST /api/v2/job_templates/{id}/launch/
  │    ├─ extra_vars = {opsflow_atom_type, params, ...}
  │    └─ 返回 job_id
  │
  ├─ TowerService.poll_job(job_id, execution_id, node_id)
  │    ├─ 自适应轮询 (3s/5s/10s/30s)
  │    ├─ WebSocket → tower_job_update (status/progress)
  │    └─ 完成/失败/超时
  │
  ├─ TowerService.extract_result(job_id)
  │    ├─ GET /artsifacts/  (set_stats 数据)
  │    ├─ GET /job_events/  (详细事件)
  │    ├─ GET /stdout/      (日志输出)
  │    └─ 返回 {status, artifacts, events, stdout, summary}
  │
  └─ 返回 ExecuteResult(success, data)
       └─ data.outputs 包含 {stdout, artifacts, summary, ...}
            └─ flow_engine 注入 context[node_id] = {status, artifacts}
```

## 关键设计决策

### 1. 迁移到 BambooDjangoRuntime

原 FlowEngine 实现了一个自定义 Pipeline Tree 解释器，手动解析 activities/gateways/flows、用 Redis 计数器实现 ConvergeGateway、用 Celery group 实现 ParallelGateway。这套逻辑本质上是重新实现了 bamboo-pipeline 的 `BambooDjangoRuntime`。

**迁移后**: delegating to `BambooDjangoRuntime` + `api.run_pipeline()`。

| 旧实现 | 新实现 |
|--------|--------|
| `_execute_bamboo()` 手动遍历 | `api.run_pipeline(runtime, pipeline)` |
| `_execute_activity()` 直接调 Service | BambooDjangoRuntime.ActivityMixin |
| `_execute_exclusive()` 条件遍历 | BambooDjangoRuntime.GatewayMixin |
| `_execute_parallel()` Celery group | BambooDjangoRuntime.GatewayMixin |
| `_execute_converge()` Redis 计数器 | BambooDjangoRuntime.ConvergeMixin |
| `_set_node_status()` 手动状态管理 | BambooDjangoRuntime.StateMixin + post_set_state 信号 |

节点状态追踪通过 `pipeline.eri.signals.post_set_state` 信号异步完成，`signals.py` 中的 `on_post_set_state` 处理器将 bamboo 状态映射到 FlowExecution 状态。

### 2. Executor Factory 模式

原子层通过 Factory Pattern 实现多平台支持：

```
meta.json (executor_type)
  → AtomExecutorFactory
    → importlib.import_module 惰性加载
    → BaseExecutor.execute()
    → ExecuteResult(success, data, error)
```

新增平台只需：写 `*_executor.py` 继承 `BaseExecutor` → 注册到 FACTORY 字典 → 创建 `meta.json`（`executor_type` 指向新类名）。

### 3. Component 注册机制

通过 `pipeline.component_framework.Component` 元类将原子注册到全局 ComponentLibrary：

```
ATOM_REGISTRY (meta.json 扫描)
  → register_atom_services()
    → type() 动态创建 Component 子类
      → ComponentMeta 自动注册到 ComponentLibrary + ComponentModel
        → BambooDjangoRuntime.get_service(code) 查询 Service
```

每个原子共享同一 `AnsibleAtomService` 基类执行逻辑，通过 `_atom_name` 区分类型。

### 4. AI 集成

- 使用 DeepSeek via OpenAI-compatible API
- `response_format={'type': 'json_object'}` 保证输出 JSON
- System Prompt 动态注入可用原子列表（从 AtomRegistry 读取，排除 `shell` 原子防止 AI 用作 fallback）
- SafetyGuard 后端校验，包含白名单/高危/备份检查
- 多重 AI 幻觉防御:
  - `_errors` 字段检测: AI 无法完成请求时生成 `_errors`，后端拒绝保存
  - Shell 原子过滤: 从 AI 可见原子列表移除 `shell` + 服务端二次拦截
  - 跨平台误用检测: 用户输入含 VM/虚拟机 时拦截 AI 使用 netapp_* 原子
- RAG 搜索 OpsKnowledge 注入相关案例
