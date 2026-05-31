# 核心引擎详解

## 1. FlowEngine — 流程执行引擎

**文件**: `backend/opsflow/core/flow_engine.py`

### 职责

将 `build_bamboo_pipeline()` 生成的 Pipeline Tree 提交给 `BambooDjangoRuntime` + `api.run_pipeline()` 执行。节点调度、状态机、网关逻辑全部由 BambooDjangoRuntime 内部处理。

### 外部接口

```python
engine = FlowEngine(execution)
engine.start()      # 启动（写入状态 + 提交 Celery 任务）
engine.pause()      # 暂停 → api.pause_pipeline()
engine.resume()     # 恢复 → api.resume_pipeline()
engine.retry(node_id)   # 重试 → api.retry_node()
engine.skip(node_id)    # 跳过 → api.skip_node()
engine.cancel()     # 取消终止 → api.revoke_pipeline() + 标记 cancelled
```

### 执行流程

```
FlowEngine.run()
  │
  ├─ build_bamboo_pipeline(template) → Pipeline Tree dict
  │    └─ 内部调用 apply_node_timout_configs() 注入超时配置
  ├─ 保存 bamboo_pipeline_id 到 execution.context
  │
  └─ api.run_pipeline(runtime=BambooDjangoRuntime(), pipeline=pipeline)
       │
       │  BambooDjangoRuntime (异步调度到 Celery):
       │  ├─ ProcessMixin → 创建 Process + Node 记录（MySQL）
       │  ├─ TaskMixin   → 发送到 Celery er_execute/er_schedule 队列
       │  ├─ StateMixin  → 状态机: READY→RUNNING→FINISHED/FAILED
       │  │                 每次转换发送 post_set_state + pipeline_event 信号
       │  ├─ ActivityMixin → get_service(code) → Component
       │  │                    → bound_service → AnsibleAtomService.execute()
       │  │                    → data.outputs 回写 ERI Data 模型
       │  ├─ GatewayMixin  → ExclusiveGateway: 表达式求值选择分支
       │  │                    ParallelGateway: 扇出所有分支
       │  │                    ConvergeGateway: 自动汇聚
       │  └─ 根节点完成 → 流程结束
       │
       └─ run_pipeline 立即返回（实际执行在 Celery 中异步进行）

节点状态变更（异步，通过 post_set_state + pipeline_event 信号）:
    └─ signals.py → _handle_root_state_change() → 更新 FlowExecution.status
    └─ signals.py → _log_node_result() → get_execution_data_outputs() 读取 → OpsLog
    └─ signals.py → _notify_node_status() + _notify_completed() → WS 推送

## 2. BambooBuilder — Pipeline Tree 构建器

**文件**: `backend/opsflow/core/bamboo_builder.py`

### 输入/输出格式

**输入**（从前端 X6 画布获取）:
```json
{
  "nodes": [
    {"id": "node_1", "label": "Check Disk", "node_type": "", "atom_type": "disk_check", "params": {}},
    {"id": "node_2", "label": "Pass?", "node_type": "exclusive_gateway"},
    {"id": "node_3", "label": "Parallel", "node_type": "parallel_gateway"},
    {"id": "node_4", "label": "Converge", "node_type": "converge_gateway"}
  ],
  "edges": [
    {"from": "node_1", "to": "node_2", "label": "success"},
    {"from": "node_2", "to": "node_3", "label": "success"},
    {"from": "node_2", "to": "node_4", "label": "failure"}
  ]
}
```

**输出**（bamboo-engine 标准格式）:
```json
{
  "id": "...",
  "start_event": {"id": "...", "outgoing": "flow_..."},
  "end_event": {"id": "..."},
  "activities": {
    "node_1": {"type": "ServiceActivity", "component": {"code": "opsflow_disk_check", "inputs": {}}, "outgoing": "flow_..."}
  },
  "gateways": {
    "node_2": {"type": "ExclusiveGateway", "outgoing": ["flow_...", "flow_..."], "conditions": {...}},
    "node_3": {"type": "ParallelGateway", "outgoing": ["flow_...", "flow_..."]},
    "node_4": {"type": "ConvergeGateway", "outgoing": "flow_..."}
  },
  "flows": {
    "flow_1": {"source": "node_1", "target": "node_2"},
    "flow_2": {"source": "node_2", "target": "node_3"},
    "flow_3": {"source": "node_2", "target": "node_4"}
  },
  "data": {"inputs": {"target_hosts": [], "global_vars": {}}}
}
```

## 3. AnsibleAtomService — Service 实现

**文件**: `backend/opsflow/core/atom_service.py`

### 注册机制

通过 `pipeline.component_framework.Component` 元类注册，由 `apps.py.ready()` 在启动时调用 `register_atom_services()` 扫描 `ATOM_REGISTRY` 为每个原子动态创建 Component 子类：

```python
# atom_service.py
class AnsibleAtomService(Service):
    """基类 Service — 所有原子共享此实现，通过 _atom_name 区分类型"""
    def execute(self, data, parent_data):
        params = dict(data.inputs)
        atom_name = getattr(self, '_atom_name', 'unknown')
        result = AtomExecutorFactory.execute_atom(atom_name, params, ...)
        data.outputs.update({...})
        return result.success

# 启动时动态创建：
#   type("DiskCheckComponent", (Component,), {
#       'name': 'disk_check',
#       'code': 'opsflow_disk_check',
#       'bound_service': AnsibleAtomService,
#       '__module__': 'opsflow.core.atom_service',
#   })
```

BambooDjangoRuntime 在运行时通过 `get_service(code)` 查找 ComponentLibrary → `bound_service` → Service 实例。

Service 还定义 `inputs_format()` / `outputs_format()` 描述接口契约：

```python
def inputs_format(self):
    return [
        InputItem(name="原子类型", key="_atom_type", type="string", required=True),
        InputItem(name="目标主机", key="target_hosts", type="array", required=False),
    ]

def outputs_format(self):
    return [
        OutputItem(name="标准输出", key="stdout", type="string"),
        OutputItem(name="返回码", key="returncode", type="int"),
    ]
```

### 执行流程

```
service.execute(data, root_data)
  │
  ├─ 从 data.inputs 提取 params
  ├─ 注入 _atom_type 标识原子类型
  ├─ 调用 AtomExecutorFactory.execute_atom(atom_name, inputs, target_hosts)
  │    │
  │    ├─ 根据 executor_type（从 meta.json 读取）分发到对应执行器:
  │    │   "ansible" → AnsibleExecutor → ansible_trigger → TowerService
  │    │   "esxi"    → EsxiExecutor (伪代码)
  │    │   "netapp"  → NetAppExecutor (伪代码)
  │    │   "servicenow" → ServiceNowExecutor (骨架)
  │    │   "redfish" → RedfishExecutor (骨架)
  │    │   "http"    → HttpExecutor (通用 REST)
  │    │
  │    ├─ AnsibleExecutor 执行详情:
  │    │   1. ansible_trigger.execute_atom()
  │    │   2.  → TowerService.launch_job()  POST /launch/
  │    │   3.  → TowerService.poll_job()    自适应间隔轮询
  │    │   4.  → TowerService.extract_result() artifacts/events/stdout
  │    │   5.  → 返回 {stdout, stderr, returncode, artifacts, summary}
  │    │
  │    └─ 返回 ExecuteResult(success, data)
  │
  └─ data.outputs 更新: stdout, stderr, returncode, _result, executor_output
  └─ 返回 result.success
```

## 4. TowerService — Ansible Tower REST API 封装

**文件**: `backend/opsflow/core/tower_service.py`

### 职责

封装 Tower (AWX) REST API，提供作业触发、状态轮询、结果提取的统一接口。

### 方法

| 方法 | 说明 |
|------|------|
| `launch_job(template_id, extra_vars)` | POST job_templates/{id}/launch/ |
| `poll_job(job_id, timeout, execution_id, node_id)` | 自适应间隔轮询 + WebSocket 推送 |
| `get_job_status(job_id)` | GET jobs/{id}/ |
| `get_artifacts(job_id)` | GET jobs/{id}/artifacts/ (set_stats 数据) |
| `get_job_events(job_id, page_size)` | GET jobs/{id}/job_events/（分页） |
| `get_stdout(job_id, max_length)` | GET jobs/{id}/stdout/?format=txt |
| `extract_result(job_id)` | 合并 artifacts/events/stdout/summary |
| `cancel_job(job_id)` | POST jobs/{id}/cancel/ |

### 自适应轮询间隔

| 时间段 | 间隔 | 说明 |
|--------|------|------|
| 0~30s | 3s | 快速感知启动 |
| 30s~5min | 5s | 正常等待 |
| 5min~30min | 10s | 长任务慢下来 |
| 30min+ | 30s | 超长任务保底 |

轮询过程中通过 Django Channels 持续推送 `tower_job_update` 消息到前端。

## 5. Executor Factory — 多平台原子执行器

**文件**: `backend/opsflow/core/executors/factory.py`

### 架构

```
AtomExecutorFactory
  │
  ├─ get_executor(executor_type) → BaseExecutor 子类（惰性加载 + 缓存）
  │
  ├─ execute_atom(atom_name, inputs, target_hosts)
  │    1. 从 atom_registry 读取 meta（含 executor_type）
  │    2. 根据 executor_type 获取执行器
  │    3. validate_inputs()
  │    4. executor.execute()
  │    5. 返回 ExecuteResult
  │
  └─ rollback_atom(atom_name, inputs, context)
```

### 执行器列表

| executor_type | 类 | 状态 | 依赖 |
|--------------|-----|------|------|
| `ansible` | `AnsibleExecutor` | 具体实现 | ansible_trigger → TowerService |
| `http` | `HttpExecutor` | 具体实现 | requests |
| `esxi` | `EsxiExecutor` | 伪代码 | pyVmomi |
| `netapp` | `NetAppExecutor` | 伪代码 | ONTAP REST API |
| `servicenow` | `ServiceNowExecutor` | 骨架 | pysnow |
| `redfish` | `RedfishExecutor` | 骨架 | redfish |
| `test` | `TestExecutor` | 具体实现 | 无（流程引擎测试） |

### BaseExecutor 契约

```python
class BaseExecutor:
    executor_type: str = ""
    def execute(self, inputs: dict) -> ExecuteResult: ...
    def rollback(self, inputs: dict, context: dict) -> ExecuteResult: ...
    def validate_inputs(self, meta_inputs, actual_inputs) -> list[str]: ...

@dataclass
class ExecuteResult:
    success: bool
    data: dict = field(default_factory=dict)
    error: str = ""
```

## 6. AtomRegistry — 原子注册中心

**文件**: `backend/opsflow/core/atom_registry.py`

### 扫描机制

```python
# 启动时由 apps.py 调用
scan_atoms()
  │
  └─ 扫描 ansible_atoms/atoms/*/meta.json
       │
       ├─ 每个 meta.json 格式:
       │   {
       │     "name": "disk_check",
       │     "description": "Check disk usage",
       │     "risk_level": "low",
       │     "group": "check",
       │     "component_code": "opsflow_disk_check",
       │     "executor_type": "ansible",     # ← 路由到对应执行器
       │     "inputs": [{"name": "threshold", "type": "int"}],
       │     "rollback": null
       │   }
       │
       └─ 填充全局 ATOM_REGISTRY dict
```

`executor_type` 默认 `"ansible"`（向后兼容），未指定时自动使用 AnsibleExecutor。

### 注册原子（37 个）

**Ansible 原子（13 个，executor_type=ansible）**:

| 原子 | 分组 | 风险 | 说明 |
|------|------|------|------|
| disk_check | check | low | 磁盘检查 |
| ping_test | check | low | 网络连通性测试 |
| health_check | check | low | 服务健康检查 |
| shell | action | medium | 执行 Shell 命令 |
| upload_file | action | medium | 上传文件 |
| file_copy | action | medium | 复制文件 |
| script_exec | action | medium | 执行脚本 |
| backup_file | action | low | 文件备份 |
| java_deploy | action | high | Java 应用部署 |
| docker_deploy | action | high | Docker 部署 |
| nginx_reload | action | medium | Nginx 重载 |
| service_control | control | high | 服务启停控制 |
| send_alert | control | low | 发送告警通知 |

**ESXi 原子（5 个，executor_type=esxi）**:

| 原子 | 分组 | 风险 | 说明 |
|------|------|------|------|
| esxi_create_vm | vm | high | 创建虚拟机 |
| esxi_destroy_vm | vm | high | 删除虚拟机 |
| esxi_power_on | vm | medium | 开机 |
| esxi_power_off | vm | medium | 关机 |
| esxi_get_state | vm | low | 查询 VM 状态 |

**NetApp 原子（5 个，executor_type=netapp）**:

| 原子 | 分组 | 风险 | 说明 |
|------|------|------|------|
| netapp_create_volume | storage | high | 创建 FlexVol 卷 |
| netapp_delete_volume | storage | high | 删除卷 |
| netapp_get_volume | storage | low | 查询卷详情 |
| netapp_create_snapshot | storage | low | 创建快照 |
| netapp_modify_volume | storage | high | 修改卷属性（扩容/策略） |

**ServiceNow 原子（5 个，executor_type=servicenow）**:

| 原子 | 分组 | 风险 | 说明 |
|------|------|------|------|
| servicenow_create_incident | itsm | medium | 创建 Incident |
| servicenow_update_incident | itsm | medium | 更新 Incident |
| servicenow_get_incident | itsm | low | 查询 Incident |
| servicenow_create_change_request | itsm | high | 创建 Change Request |
| servicenow_get_cmdb_ci | itsm | low | 查询 CMDB CI |

**Redfish 原子（7 个，executor_type=redfish）**:

| 原子 | 分组 | 风险 | 说明 |
|------|------|------|------|
| redfish_get_system_info | bmc | low | 查询系统信息 |
| redfish_power_on | bmc | high | 服务器开机 |
| redfish_power_off | bmc | high | 服务器关机 |
| redfish_power_cycle | bmc | high | 服务器重启 |
| redfish_set_boot_device | bmc | medium | 设置启动设备 |
| redfish_list_storage | bmc | low | 查询存储列表 |
| redfish_firmware_inventory | bmc | low | 固件清单 |

**HTTP 原子（1 个，executor_type=http）**:

| 原子 | 分组 | 风险 | 说明 |
|------|------|------|------|
| http_api_call | generic | medium | 通用 REST API 调用 |

**Test 原子（1 个，executor_type=test）**:

| 原子 | 分组 | 风险 | 说明 |
|------|------|------|------|
| test_print_time | test | low | 打印当前时间，流程引擎功能验证 |

## 7. SafetyGuard — 安全校验器

**文件**: `backend/opsflow/core/safety_guard.py`

### 校验规则

| 规则 | 类型 | 说明 |
|------|------|------|
| 原子白名单 | error | 不在 ATOM_REGISTRY 中的原子类型 |
| 重试上限 | error | max_retries > 10 |
| 高危回滚路径 | warning | 高危原子没有 failure/rollback 出边 |
| 备份前置 | warning | 需要备份的原子前缺少 backup_file |
| 孤儿节点 | warning | 非起始节点无入边 |
| Shell 原子拦截 | error | AI 不应生成 shell 原子（作为不存在的功能 fallback） |
| 跨平台误用检查 | error | 用户输入含 VM/虚拟机 时，禁止使用 netapp_* 原子 |

## 8. Layout Engine — Sugiyama 分层布局引擎

**文件**: `backend/opsflow/core/layout/`

### 架构

适配 bk_sops `pipeline_web/drawing_new` 的 Sugiyama 分层图绘制算法，提供确定性的节点自动定位，替代早期基于 LLM 的布局方案。

### 5 阶段流程

```
输入: pipeline dict (activities, gateways, flows)
  │
  ├─ 1. Normalize → 构建 all_nodes 统一字典
  ├─ 2. Acyclic   → 自环边移除 + 反向边逆转（DFS 环检测）
  ├─ 3. Rank      → 最长路径层级分配 + 可行树优化
  ├─ 4. Order     → 加权中位数交叉最小化（24 次迭代）
  ├─ 5. Dummy     → 虚拟节点替换长跨度边
  └─ 6. Position  → 坐标分配 + 箭头端点计算
       │
       └─ 输出: location[{id, x, y}]
```

### 入口函数

```python
compute_layout(nodes, edges) → list[{id, x, y}]
```

由 `layout_adapter.py` 桥接 OPSflow `{nodes, edges}` 格式与引擎内部 pipeline 格式：

```
opsflow_to_pipeline(nodes, edges)    # OPSflow → 引擎格式
  → draw_pipeline(pipeline, sizes)   # Sugiyama 5 阶段
  → pipeline_to_positions(pipeline)  # 提取坐标
```

### 节点尺寸

| 类型 | 尺寸 (w×h) | shift_y (层间距) |
|------|-----------|-----------------|
| 原子(atom) | 180×48 | 144 (96px gap) |
| 事件(event) | 56×56 | 自动居中 |
| 网关(gateway) | 70×70 | 自动居中 |
| shift_x (列间距) | 270 | — |

### 边界处理

- 0-1 节点: 直接返回默认坐标，不进入引擎
- 无效边引用: 抛出 `ValueError`
- 大量节点(>500): 引擎仍可运行，记录性能警告
- 缺失起止节点: `layout_adapter.py` 自动合成

## 9. Pipeline Contrib 集成

**配置文件**: `backend/application/settings.py`

已注册的 pipeline contrib apps:

| App | 功能 | 启动配置 |
|-----|------|----------|
| `pipeline.contrib.rollback` | 流程回滚 API（TOKEN/ANY 模式） | `PIPELINE_ENABLE_ROLLBACK = True` |
| `pipeline.contrib.node_timeout` | 节点超时强制结束/跳过 | 通过 `apply_node_timout_configs()` 注入 |
| `pipeline.contrib.engine_admin` | 引擎管理 UI（暂停/恢复/重试/跳过） | 无 |

### 事件信号

启用 `ENABLE_PIPELINE_EVENT_SIGNALS = True` 后，bamboo-engine 发送 `pipeline_event` 信号提供 30+ 事件类型：

| 事件 | 说明 |
|------|------|
| `pre_run_pipeline` / `pipeline_finish` | 流程启动/结束 |
| `pre_pause_pipeline` / `pre_resume_pipeline` | 暂停/恢复流程 |
| `node_enter` / `node_finish` | 节点进入/完成 |
| `node_execute_fail` / `node_schedule_fail` | 节点执行/调度失败 |
| `pre_retry_node` / `pre_skip_node` | 重试/跳过节点 |

## 10. SchedulerService — 定时调度器

**文件**: `backend/opsflow/core/scheduler_service.py`

### 职责

基于 APScheduler 的定时任务调度器，用于自动触发 SchedulePlan 的执行。

### 架构

```
OpsflowScheduler
  │
  ├─ BackgroundScheduler (后台线程, timezone=Asia/Shanghai)
  │    └─ DjangoJobStore (调度记录持久化到 MySQL)
  │
  ├─ start()
  │    ├─ _register_existing_plans() → 加载 DB 中 ACTIVE 的调度计划
  │    └─ scheduler.start()
  │
  ├─ add_plan(plan)   → 构建 DateTrigger 或 CronTrigger → 注册 Job
  ├─ update_plan(plan) → remove + add
  ├─ remove_plan(plan) → scheduler.remove_job()
  ├─ pause_plan(plan)  → scheduler.pause_job()
  └─ resume_plan(plan) → scheduler.resume_job()
```

### 触发机制

```python
# APScheduler 回调
_execute_plan(plan_id)
  │
  ├─ 加载 SchedulePlan (含 template + created_by)
  ├─ 检查 template.is_draft → 草稿跳过，一次性任务标记 completed
  ├─ 创建 FlowExecution (status=PENDING)
  ├─ FlowEngine.start(sync=False) → Celery 异步执行
  ├─ 更新 last_run_at / total_run_count
  ├─ 一次性任务 → status=COMPLETED
  └─ 重试支持 → retry_schedule_execution Celery 任务
```

### 启动方式

| 方式 | 设置/命令 | 适用环境 |
|------|-----------|----------|
| 自启动 | `OPSFLOW_SCHEDULER_AUTOSTART = True` | 开发 |
| 独立进程 | `python manage.py start_opsflow_scheduler` | 生产（Redis 锁防重复） |

### 触发器构建

```python
def _build_trigger(self, plan):
    if plan.schedule_type == 'one_time':
        return DateTrigger(run_date=plan.scheduled_at, timezone=plan.timezone)
    return CronTrigger.from_crontab(plan.cron_expr, timezone=plan.timezone)
```

调度器未启动时，`_sync_next_run()` 兜底手动计算 `next_run_at`（一次性直接用 scheduled_at，周期性用 CronTrigger 推算）。

## 11. LLM Service — AI 服务

**文件**: `backend/opsflow/core/llm_service.py`

### AI 幻觉防御

| 层 | 机制 | 说明 |
|----|------|------|
| Prompt | 平台匹配规则 | esxi_* → VM, netapp_* → 存储, redfish_* → 物理服务器 |
| Prompt | Shell 排除 | 已从 AI 可见原子列表中删除 `shell`，防止用作 fallback |
| Prompt | _errors 替代 | AI 无法完成时生成 `_errors` 字段，而非使用替代原子 |
| Prompt | 增量修改指令 | refine_pipeline 明确以 "迭代修改" 方式处理，保留现有节点 ID，不重新生成 |
| 服务端 | _errors 检测 | `create_from_ai`/`refine` 端点检查 pipeline._errors |
| 服务端 | Shell 拦截 | 任何包含 `atom_type=shell` 的响应被拒绝 |
| 服务端 | 跨平台检查 | 用户语义(VM/虚拟机)与 AI 生成原子(netapp_*)不匹配时拒绝 |
