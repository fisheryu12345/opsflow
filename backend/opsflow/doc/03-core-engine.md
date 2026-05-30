# 核心引擎详解

## 1. FlowEngine — 流程执行引擎

**文件**: `backend/opsflow/core/flow_engine.py`

### 职责

将 `build_bamboo_pipeline()` 生成的 Pipeline Tree 作为输入，按节点类型分发到不同的处理方法。

### 外部接口

```python
engine = FlowEngine(execution)
engine.start()      # 启动（写入状态 + 提交 Celery 任务）
engine.resume()     # 恢复暂停
engine.retry(node_id)   # 重试失败节点
engine.skip(node_id)    # 跳过节点
```

### 内部方法链

```
run()
  └─ build_bamboo_pipeline(template) → Pipeline Tree dict
  └─ _execute_bamboo(pipeline)
       └─ 从 start_event.outgoing 找到第一个节点
            └─ _process_node(node_id, pipeline, converge_key)
                 ├─ activities[node_id] → _execute_activity()
                 ├─ gateways[node_id]   → _execute_gateway()
                 └─ end_event          → _complete()
```

### 活动节点执行 _execute_activity

```
1. 从 activity.component.inputs 提取参数
2. 注入 _execution_id / _node_id（供 Tower 轮询 WS 推送）
3. 构造 ExecutionData
4. _set_node_status(node_id, "running")
5. _notify_node(node_id, "running")  → WebSocket 推送
6. service = get_service(code)       → AnsibleAtomService
7. success = service.execute(data, root_data)  → Tower 异步执行 + 轮询
8. 记录 outputs._result + Tower artifacts
9. artifacts 注入 context["node_id"] = {status, artifacts, ...}
10. 成功 → "completed" / 失败 → "failed" → WebSocket 推送
11. 检查 pause 状态
12. 走 success/failure 出边到下一个节点
```

### 条件求值 _evaluate_condition

支持完整的 `${...}` 表达式语法：

| 表达式 | 示例 | 说明 |
|--------|------|------|
| `${_result}` | `${_result == True}` | 基础成功/失败 |
| `${path.artifacts.key}` | `${check_space.artifacts.available_gb >= 2}` | 引用前序节点 artifacts |
| `${path.structured.key}` | `${health_check.structured.status == "healthy"}` | 引用 stdout 解析 JSON |
| `${path.summary.field}` | `${disk_check.summary.failed > 0}` | 事件统计比较 |

Context 注入：`_execute_activity()` 将 Tower artifacts 的每个字段按 `node_id.key` 展开到 context，同时完整结构存入 `context[node_id]`。

### 网关执行逻辑

```
_exclusive_gateway:
  多条出边 → 遍历 conditions，匹配 _result 或条件表达式
  命中条件 → 走该分支
  无命中 → 走 is_default 或第一条

_parallel_gateway:
  BFS 查找下游 ConvergeGateway
  设 Redis 计数 = 分支数
  Celery group 并行执行所有分支

_conditional_parallel_gateway:
  按 conditions 筛选出边
  其余同 parallel

_converge_gateway:
  Redis decr 原子减一
  remaining > 0 → 当前分支结束（等待其他分支）
  remaining == 0 → 清理计数，继续执行后续节点
```

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

### 实现接口

实现 `bamboo_engine.eri.Service` 接口:
- `execute()`: 核心方法，通过 `AtomExecutorFactory` 根据 executor_type 自动分派
- `schedule()`: 轮询/回调（当前直接返回）
- `need_schedule()`: 当前返回 False（一次性执行，轮询在 execute() 内部完成）

### 执行流程

```
service.execute(data, root_data)
  │
  ├─ 从 data.inputs 提取 params
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

### 注册原子（31 个）

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

## 8. LLM Service — AI 服务

**文件**: `backend/opsflow/core/llm_service.py`

### 功能

| 方法 | 说明 |
|------|------|
| `generate_pipeline(nl_input, target_hosts)` | 自然语言 → Pipeline Tree JSON |
| `refine_pipeline(nl_input, nodes, edges, target_hosts)` | 多轮对话修改现有流程 |
| `optimize_layout(nodes, edges)` | AI 布局优化（BFS 分层） |
| `analyze_pipeline(nodes, edges)` | 分析流程步骤、风险、建议 |
| `rag_search(query)` | 知识库 RAG 检索 |

### AI 幻觉防御

| 层 | 机制 | 说明 |
|----|------|------|
| Prompt | 平台匹配规则 | esxi_* → VM, netapp_* → 存储, redfish_* → 物理服务器 |
| Prompt | Shell 排除 | 已从 AI 可见原子列表中删除 `shell`，防止用作 fallback |
| Prompt | _errors 替代 | AI 无法完成时生成 `_errors` 字段，而非使用替代原子 |
| 服务端 | _errors 检测 | `create_from_ai`/`refine` 端点检查 pipeline._errors |
| 服务端 | Shell 拦截 | 任何包含 `atom_type=shell` 的响应被拒绝 |
| 服务端 | 跨平台检查 | 用户语义(VM/虚拟机)与 AI 生成原子(netapp_*)不匹配时拒绝 |
