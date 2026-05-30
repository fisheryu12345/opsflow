# 系统架构设计

## 整体架构

OpsFlow 采用**前后端分离 + 异步任务 + WebSocket 推送 + 多平台原子层**的架构。

```
┌───────────────┐     REST API      ┌──────────────────┐     Celery      ┌──────────────┐
│   Vue 3 X6    │ ◄──────────────►  │  Django Backend  │ ◄─────────────► │    Worker    │
│   Design      │                   │                  │                 │              │
│   Canvas      │ ◄─── WebSocket ──► │  Channels        │                 │  Pipeline    │
│               │  (状态实时推送)    │  Consumer        │                 │  Execution   │
│   Monitor     │                   └──────────────────┘                 │              │
│   Canvas      │                         │                              │  Notify      │
└───────────────┘                         │                              └──────────────┘
                                          ▼
                                   ┌──────────────┐
                                   │    Redis     │
                                   │  (Converge   │
                                   │   Counter)   │
                                   └──────────────┘
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
- **FlowEngine**: 流程执行引擎，处理串行、条件、并行、汇聚
- **AnsibleAtomService**: 实现 bamboo-engine Service 接口，桥接原子执行
- **TowerService**: Ansible Tower (AWX) REST API 封装（触发/轮询/结果提取）

### 4. 原子层

- **AtomRegistry**: 从 `ansible_atoms/atoms/*/meta.json` 加载原子元数据（含 executor_type 字段）
- **Executor Factory**: 根据 executor_type 自动分发到对应执行器（Ansible/ESXi/NetApp/ServiceNow/Redfish/HTTP/Test）
- **Atomic Executor**: 各平台执行器实现统一 `execute()/rollback()` 接口

### 5. 数据层

- **MySQL**: FlowTemplate、FlowExecution、OpsLog、OpsKnowledge
- **Redis**: 并行汇聚计数、Celery 消息队列、Tower 并发信号量

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
    │
    └─ _execute_bamboo(pipeline)
         │
         ├─ _process_node(start_event.outgoing.target, pipeline)
         │
         │  ┌─────────────────────────────────────────────────┐
         │  │              Node Dispatch                      │
         │  │                                                 │
         │  │  activities[node_id]  →  _execute_activity()    │
         │  │  gateways[node_id]                             │
         │  │    ├─ ExclusiveGateway  →  _execute_exclusive() │
         │  │    ├─ ParallelGateway   →  _execute_parallel()  │
         │  │    ├─ ConditionalParallel → _execute_cond_par() │
         │  │    └─ ConvergeGateway   →  _execute_converge()  │
         │  │  end_event  →  _complete()                      │
         │  └─────────────────────────────────────────────────┘
         │
         ├─ 每个 activity 执行:
         │    1. _set_node_status(node_id, "running")
         │    2. _notify_node(node_id, "running")  ← WebSocket
         │    3. service = get_service(code) → AnsibleAtomService
         │    4. → AtomExecutorFactory → AnsibleExecutor
         │    5.   → TowerService.launch_job()  POST /launch/
         │    6.   → TowerService.poll_job()    自适应轮询
         │    7.     ├─ 每 3~30 秒 GET /jobs/{id}/
         │    8.     └─ WebSocket tower_job_update (进度)
         │    9.   → TowerService.extract_result() artifacts
         │    10.  → 结果注入 context
         │    11. 成功 → "completed" / 失败 → "failed"
         │    12. _notify_node()  ← WebSocket
         │    13. _process_node(next_node)
         │
         └─ 完成 → _complete()
              ├─ execution.status = "completed"
              ├─ execution.ended_at = now()
              └─ _notify_completed()  ← WebSocket
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

### 1. 为什么不用 bamboo-engine 的 ERI Runtime？

bamboo-engine 的 `EngineRuntimeInterface` 有 60+ 方法（get_context、get_activity、set_state 等），实现复杂度过高。替代方案：

- 将 FlowEngine 直接作为 **Pipeline Tree 解释器**，不走 ERI 层
- 用 `AnsibleAtomService.execute()` 直接执行原子（复用 Service 接口但不需要完整的 Runtime）
- 用 **Redis 计数器** 替代 ERI 的并发控制机制来实现 ConvergeGateway

### 2. 并行分支的实现

```
ParallelGateway
    │
    ├─ branch_1 → ... → ConvergeGateway  \
    ├─ branch_2 → ... → ConvergeGateway   ├─ Redis counter (N=3)
    └─ branch_3 → ... → ConvergeGateway  /
                                          │
                          每个分支到达时 decr 计数
                          当 remaining == 0 时，最后到达的分支继续执行
```

- 使用 Celery `group()` 实现真正并行
- Redis 原子操作 `decr()` 保证并发安全
- `_find_converge_target()` BFS 自动查找汇聚网关

### 3. 条件评估

ExclusiveGateway 和 ConditionalParallelGateway 支持完整表达式语法：

```
${_result == True}                       → 基础成功/失败
${check_space.artifacts.available_gb >= 2}  → 引用前序节点 artifacts
${health_check.structured.status == "healthy"} → stdout JSON 解析值
${disk_check.summary.failed > 0}         → 事件统计
```

Context 中的 `_last_result` 记录上一个节点的执行结果；Gateway 遍历 conditions 匹配条件，命中则走对应分支，未命中走 `is_default` 或第一条出边。

### 4. Executor Factory 模式

原子层通过 Factory Pattern 实现多平台支持：

```
meta.json (executor_type)
  → AtomExecutorFactory
    → importlib.import_module 惰性加载
    → BaseExecutor.execute()
    → ExecuteResult(success, data, error)
```

新增平台只需：写 `*_executor.py` 继承 `BaseExecutor` → 注册到 FACTORY 字典 → 创建 `meta.json`（`executor_type` 指向新类名）。

### 5. AI 集成

- 使用 DeepSeek via OpenAI-compatible API
- `response_format={'type': 'json_object'}` 保证输出 JSON
- System Prompt 动态注入可用原子列表（从 AtomRegistry 读取，排除 `shell` 原子防止 AI 用作 fallback）
- SafetyGuard 后端校验，包含白名单/高危/备份检查
- 多重 AI 幻觉防御:
  - `_errors` 字段检测: AI 无法完成请求时生成 `_errors`，后端拒绝保存
  - Shell 原子过滤: 从 AI 可见原子列表移除 `shell` + 服务端二次拦截
  - 跨平台误用检测: 用户输入含 VM/虚拟机 时拦截 AI 使用 netapp_* 原子
- RAG 搜索 OpsKnowledge 注入相关案例
