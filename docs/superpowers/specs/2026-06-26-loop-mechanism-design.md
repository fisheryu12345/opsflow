# 流程循环机制 — 设计文档

> 日期: 2026-06-26 | 类型: 功能设计 | 涉及 App: opsflow

---

## 背景

OpsFlow 基于 bamboo-engine（DAG 引擎），不支持有向图中的环路。但运维自动化场景中循环是刚需：
- **场景 A：** 批量执行（ping N 台机器、分批回滚）—— 同个原子重复执行 N 次
- **场景 B：** 条件驱动持续执行（轮询任务状态、等待审批）—— 需要排他网关回环

两种场景本质不同，需要两种机制支持。

## 总体设计

| 特性 | 机制 A（节点级） | 机制 B（排他网关） |
|------|---------------|-----------------|
| 循环体 | 单个原子节点 | 任意子网（多个节点） |
| 终止方式 | `loop_times` 固定次数 | 条件表达式满足 |
| 参数注入 | `loop_var.values` 按次替换 | 直接引用节点输出 |
| 前端配置 | 节点属性面板 + Loop 配置区 | 可视化画布连接回环边 |
| 对引擎影响 | 极小（loop_config 字段） | 中等（cycle_tolerate） |

---

## 一、机制 A：节点级循环

### 数据模型

在原子节点的 `params` 中新增 `loop_config`：

```json
{
  "id": "node_1",
  "node_type": "atom",
  "atom_type": "ping_test",
  "params": {
    "target_ip": "192.168.1.1",
    "loop_config": {
      "enable": true,
      "loop_times": 5,
      "loop_var": {
        "name": "target_ip",
        "values": ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
      },
      "fail_skip": false,
      "outputs_key": "outputs"
    }
  }
}
```

`loop_var.values` 的长度可以少于 `loop_times`，循环仍执行 `loop_times` 次，但值从数组中循环取（`values[i % len(values)]`）。

### 后端改动

#### `elements.py` — `_create_element()` ServiceActivity 分支

```python
loop_config = node.get('params', {}).get('loop_config', {})
if loop_config.get('enable'):
    act.loop_config = {
        'loop_times': loop_config['loop_times'],
        'fail_skip': loop_config.get('fail_skip', False),
        'outputs_key': loop_config.get('outputs_key', 'outputs'),
        # bamboo-engine 原生支持：Node.next_node_id_in_loop()
    }
    # 注册循环变量
    loop_var = loop_config.get('loop_var', {})
    if loop_var.get('name') and loop_var.get('values'):
        act.component.inputs[loop_var['name']] = Var(type=Var.SPLIT, value='${_loop_value}')
        data.inputs['${_loop_value}'] = Var(type=Var.PLAIN, value=loop_var['values'])
```

bamboo-engine 的 `ServiceActivity` handler 在 `execute()` 返回后会调用 `next_node_id_in_loop(inner_loop)`：
- 如果 `inner_loop < loop_times` → `next_node_id = self.id`（继续执行自己）
- 否则 → `next_node_id = target_nodes[0]`（往下一个节点走）

#### 循环变量注入

循环变量 `_loop_idx`（当前循环下标，从 0 开始）和 `_loop_value`（当前循环值）由引擎在每次循环前注入到执行上下文中。

`_loop_value` 的值从 `loop_var.values` 数组中取：`values[inner_loop % len(values)]`。

#### 输出聚合

每次循环的输出（outputs）通过 `outputs_key` 聚合为一个数组。默认 `outputs_key = "outputs"`，即输出存储在 `${outputs}` 上下文中。

### 前端改动

#### PropertyPanel Loop 配置

在原子节点的 Input Parameters 下方新增 Loop Config 区块：

```
┌─ Loop Configuration ─────────────────┐
│ [✓] Enable Loop                      │
│ Max iterations: [5   ]               │
│ Iterate over param: [target_ip ▼]    │
│ Values: [192.168.1.1,192.168.1.2...] │
│ On failure:  [skip ○ fail]           │
└──────────────────────────────────────┘
```

- Enable Loop 开关 → 控制整个区块的可见性
- Max iterations → loop_times
- Iterate over param → 下拉选择当前节点的 input 参数名
- Values → 逗号分隔的值列表
- On failure → fail_skip 开关

#### SubmitWizard

无影响（循环节点的参数覆盖正常生效）。

---

## 二、机制 B：排他网关图循环

### 数据模型

排他网关的条件表达式指向回已处理过的节点，形成循环：

```json
{
  "id": "gw_1",
  "node_type": "exclusive_gateway",
  "type": "exclusive_gateway",
  "params": {}
}
```

边：

```json
{"from": "gw_1", "to": "node_2", "label": "custom", "condition": "${node_2.status} != 'running'"}
{"from": "gw_1", "to": "node_3", "label": "custom", "condition": "${node_2.status} == 'running'"}
```

### Pipeline Tree 图结构

```
start → node_1 (create_ecs)
                  ↓
node_2 (check_status)
         ↓
gw_1 (ExclusiveGateway)
  ├── condition: ${node_2.status} != 'running' → back to node_2（循环）
  │
  └── condition: ${node_2.status} == 'running' → node_3（退出循环）
```

### 后端改动

#### `validation.py` — 检测循环

新增 `detect_loop_edges()` 函数，检测排他网关是否有指向已处理节点的边：

```python
def has_loop_edges(tree: dict) -> bool:
    """检测 pipeline_tree 是否有排他网关构成的循环边"""
    nodes = tree.get('nodes', [])
    edges = tree.get('edges', [])
    gateway_ids = {n['id'] for n in nodes if n.get('node_type') == 'exclusive_gateway'}
    
    # 拓扑序（忽略已有环）
    in_deg = {n['id']: 0 for n in nodes}
    for e in edges:
        in_deg[e['to']] = in_deg.get(e['to'], 0) + 1
    topo_order = []
    queue = [nid for nid, d in in_deg.items() if d == 0]
    while queue:
        nid = queue.pop(0)
        topo_order.append(nid)
        for e in edges:
            if e['from'] == nid and in_deg.get(e['to'], 0) > 0:
                in_deg[e['to']] -= 1
                if in_deg[e['to']] == 0:
                    queue.append(e['to'])
    
    topo_index = {nid: i for i, nid in enumerate(topo_order)}
    
    # 对每个排他网关的每条出边，检查目标是否在拓扑序中出现在网关之前
    for e in edges:
        if e['from'] in gateway_ids:
            if topo_index.get(e['to'], -1) < topo_index.get(e['from'], -1):
                return True
    return False
```

#### `flow_engine.py` — `run()` 方法

```python
def run(self):
    frozen = self.execution.template_snapshot or {}
    pipeline_tree = frozen.get('pipeline_tree') or ...
    
    # 检测是否有循环边
    has_loop = has_loop_edges(pipeline_tree)
    
    # 构建 pipeline（循环边会被 _topological_connect 容忍）
    pipeline = build_bamboo_pipeline(...)
    
    # 运行
    result = pipeline_api.run_pipeline(
        self._runtime, pipeline,
        cycle_tolerate=has_loop,
    )
```

#### `build_bamboo_pipeline` — 拓扑排序容忍回环

`_topological_connect()` 中，当计算后继节点的入度时，排他网关回环边的目标节点**不递减入度**，这样该节点可以同时从正向路径和回环路径到达：

```python
for s in successors:
    target_id = s['to']
    # 如果当前节点是排他网关，且目标节点在拓扑序中已出现 → 回环边
    nt = _get_node_type(effective_nodes, nid)
    if nt == 'exclusive_gateway':
        is_loopback = target_id in processed
        if is_loopback:
            continue  # 不回退入度
    in_deg[target_id] -= 1
    if in_deg[target_id] <= 0 and target_id not in processed:
        queue.append(target_id)
```

#### `_acyclic` 处理

bamboo-engine 在构建 pipeline 时会调用 `_acyclic()` 函数（`builder.py`），它会自动反转回环边的方向来通过校验。这不影响运行时行为 — 引擎的 `cycle_tolerate=True` 会让运行时正确执行环路。

### 安全限制

1. **最大迭代次数**：循环体内的排他网关条件中，引擎通过 `inner_loop` 计数，超过 `max_iterations`（默认 100）时自动失败
2. **超时保护**：节点级别的 `timeout_seconds` 正常生效，循环体总时间超限时触发 `forced_fail`
3. **前端限制**：画布中排他网关不能连接到起始节点、不能在同一两个节点间形成双向边

---

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/core/pipeline_builder/elements.py` | `_create_element()` ServiceActivity 附加 loop_config，ExclusiveGateway 常态化处理回环边 |
| `backend/opsflow/core/pipeline_builder/__init__.py` | `_topological_connect()` 容忍回环边 |
| `backend/opsflow/core/flow_engine.py` | `run()` 检测 has_loop_edges，传递 cycle_tolerate |
| `backend/opsflow/views/aliyun_views.py` | （安全机制）`_is_template_ref()` 拦截循环变量透传 |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 原子节点 Loop 配置区块 |
| `web/src/components/RenderForm/...` | 循环变量参数绑定 |

## 不涉及

- SubmitWizard 改动
- 数据库迁移
- 新的 WebSocket 或 Celery 队列

## 验证

1. **机制 A**：创建一个带 loop_config 的原子节点（ping_test loop_times=3），执行 → 验证该节点执行了 3 次，每次 IP 不同
2. **机制 B**：创建含排他网关回环的 pipeline（create → check → gateway(condition: not_done → back to check)），执行 → 验证循环直到条件满足
3. **混合**：一个 pipeline 同时包含 A 和 B 循环 → 验证两者正常工作
4. **安全限制**：`max_iterations=100` 触发时正确失败
