# 流程循环机制 — 设计文档

> 日期: 2026-06-26 | 类型: 功能设计 | 涉及 App: opsflow

---

## 背景

OpsFlow 基于 bamboo-engine（DAG 引擎），不支持有向图中的环路。但运维自动化场景中循环是刚需：

- **场景 A：批量执行** — ping N 台机器、分批回滚、批量创建 ECS。同个原子重复执行 N 次。
- **场景 B：条件驱动轮询** — 等待云主机创建完成、等待审批结果、等待 Ansible 任务结束。需要排他网关回环。

两种场景本质不同，需要两种机制支持。

---

## 总体设计

| 特性 | 机制 A（节点级） | 机制 B（排他网关） |
|------|---------------|-----------------|
| 循环体 | 单个原子节点 | 任意子网（单节点或多节点序列） |
| 终止方式 | `loop_times` 固定次数 | 条件表达式满足时退出 |
| 参数注入 | `loop_var.values` 按次替换 | 直接引用节点输出 |
| 前端配置 | PropertyPanel Loop 配置区 | 画布连接回环边 + ConditionDialog |
| 对引擎影响 | 极小（loop_config 字段） | 中等（cycle_tolerate + 拓扑容忍） |
| 失败模式 | 用户可选（严格 / fail_skip） | 条件不满足则继续循环（无失败概念） |

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

`loop_var.values` 长度可以少于 `loop_times`，循环仍执行 `loop_times` 次，值按 `values[i % len(values)]` 循环取。

### 后端改动

#### `elements.py` — `_create_element()` ServiceActivity 分支

```python
loop_config = node.get('params', {}).get('loop_config', {})
if loop_config.get('enable'):
    act.loop_config = {
        'loop_times': loop_config['loop_times'],
        'fail_skip': loop_config.get('fail_skip', False),
        'outputs_key': loop_config.get('outputs_key', 'outputs'),
    }
    loop_var = loop_config.get('loop_var', {})
    if loop_var.get('name') and loop_var.get('values'):
        act.component.inputs[loop_var['name']] = Var(type=Var.SPLIT, value='${_loop_value}')
        data.inputs['${_loop_value}'] = Var(type=Var.PLAIN, value=loop_var['values'])
```

bamboo-engine 的 `ServiceActivity` handler 调用 `next_node_id_in_loop(inner_loop)`：
- `inner_loop < loop_times` → `next_node_id = self.id`（继续执行自己）
- 否则 → `next_node_id = target_nodes[0]`（往下走）

#### 循环变量注入

`_loop_idx`（当前下标，从 0 开始）和 `_loop_value`（当前值）由引擎注入执行上下文。`_loop_value = values[inner_loop % len(values)]`。

#### 输出聚合

每次迭代的输出通过 `outputs_key` 聚合为数组。默认 `outputs_key = "outputs"`。

---

## 二、机制 B：排他网关图循环

### 数据模型

排他网关的条件表达式指向回已处理过的节点，形成循环：

```json
{"from": "gw_1", "to": "node_2", "label": "custom", "condition": "${node_2.status} != 'running'"}
{"from": "gw_1", "to": "node_3", "label": "custom", "condition": "${node_2.status} == 'running'"}
```

### Pipeline Tree 图结构

```
start → node_1 (create_ecs) → node_2 (check_status) → gw_1 (ExclusiveGateway)
                                                         │
                                    (继续循环) condition: status!=running
                                         ↓
                                    back to node_2
                                                         │
                                    (退出循环) condition: status==running
                                         ↓
                                    node_3 (init_config) → end
```

### 前端改动

#### 2a. 画布回环边样式

当前 X6 画布中边都是实线。排他网关发出的、目标节点已经在拓扑序中出现的边（回环边），应使用**虚线**样式：

```typescript
// DesignCanvas.vue 边创建逻辑
const edge = graph.addEdge({
  source: e.from,
  target: e.to,
  attrs: {
    line: {
      stroke: isBackflowEdge(e.from, e.to) ? '#E6A23C' : '#C0C4CC',
      strokeWidth: 2,
      strokeDasharray: isBackflowEdge(e.from, e.to) ? '6 3' : 'none',
      targetMarker: 'classic',
    },
  },
  ... (labels 等) ...
})
```

回环边的判定：当从 `exclusive_gateway` 发出的边时，检查 `to` 节点在拓扑序中是否位于网关之前。这在前端可以用 `useGraphCanvas` 中的工具函数实现。

#### 2b. ConditionDialog — 回环边的条件设置

当用户点击回环边打开 ConditionDialog 时，需要为该边设置**条件表达式**。当前 ConditionDialog 只支持 `success/failure/custom` 三种标签。对于回环边：

1. **条件表达式基于变量引用**：用户需要写 `${node_2.status} != 'running'` 这样的表达式
2. **条件表达式引用节点输出**：编辑器需要支持从变量浏览器中选取节点输出字段
3. **必须设置退出条件**：至少有一个排他网关的出边是退出循环的（不指向回环）

```vue
<!-- ConditionDialog 中，对于从排他网关发出的边 -->
<el-form-item v-if="isGatewayLoopback" label="Loop Condition">
  <el-input v-model="conditionExpr" placeholder="${node_2.status} == 'completed'" />
  <el-button @click="openVarBrowser"><el-icon><Search /></el-icon></el-button>
  <div class="hint-text">
    When condition is met, the flow continues along this path instead of looping.
  </div>
</el-form-item>
```

#### 2c. 画布连接限制

回环边的创建需要前端限制：

- **排除项**：不能连接到起始节点（`start_event`）
- **排除项**：不能连接到结束节点（`end_event`）
- **排除项**：不能连接到排他网关自身
- **排除项**：不能连接到排他网关的直接后继（形成瞬态环）
- **强制**：排他网关必须至少有一条**不指向回环**的出边（退出路径）

### 后端改动

#### 2d. `bamboo_validator.py` — 回环边校验

当前 `validate_bamboo_compatibility()` 用拓扑排序检测环并拒绝：

```python
# 新增：在检测到环时先判断是否是排他网关的合法回环
if loop_edges:
    # 标记为 loop edges，跳过原有拓扑校验
    logger.info("Found %d loop edges from exclusive gateways", len(loop_edges))
else:
    # 真正的非法环
    raise ValueError("流程中存在环，bamboo-engine 不支持")
```

#### 2e. `_topological_connect()` — 入度容忍

回环边的目标节点不递减入度，避免拓扑排序死锁：

```python
for s in successors:
    target_id = s['to']
    nt = _get_node_type(effective_nodes, nid)
    if nt == 'exclusive_gateway':
        is_loopback = target_id in processed
        if is_loopback:
            continue  # 不回退入度
    in_deg[target_id] -= 1
    if in_deg[target_id] <= 0 and target_id not in processed:
        queue.append(target_id)
```

#### 2f. `flow_engine.py` — `cycle_tolerate` 传递

```python
has_loop = has_loop_edges(pipeline_tree)
pipeline = build_bamboo_pipeline(...)
result = pipeline_api.run_pipeline(
    self._runtime, pipeline,
    cycle_tolerate=has_loop,
)
```

#### 2g. `acyclic.py` — Layout 回环边反转

现有的 `acyclic_run()` 会自动反转回环边方向以供布局计算。布局完成后 `acyclic_undo()` 恢复。无需改动。

### 安全限制

1. **最大迭代次数**：机制 A 的 `loop_times` + 机制 B 的 `max_iterations`（默认 100）。超出后 pipeline 自动失败。
2. **超时保护**：节点 `timeout_seconds` 正常生效，循环体超限触发 `forced_fail`。
3. **失败模式**：机制 A 支持两种模式：
   - 严格模式：某次循环失败 → pipeline 失败，等待用户处理
   - fail_skip 模式：某次循环失败 → 跳过继续下一次，记录错误到 outputs

---

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/core/pipeline_builder/elements.py` | ServiceActivity 附加 loop_config；ExclusiveGateway 正常构建回环条件 |
| `backend/opsflow/core/pipeline_builder/__init__.py` | `_topological_connect()` 容忍回环边，不递减入度 |
| `backend/opsflow/core/bamboo_validator.py` | `validate_bamboo_compatibility()` 跳过合法回环边检测 |
| `backend/opsflow/core/flow_engine.py` | `run()` 检测 `has_loop_edges()`，传递 `cycle_tolerate` |
| `web/src/views/apps/opsflow/composables/useGraphCanvas.ts` | 新增 `isBackflowEdge()` 工具函数 + 边虚线样式 |
| `web/src/views/apps/opsflow/components/gates/ConditionDialog.vue` | 回环边条件表达式编辑 + 变量浏览器入口 |
| `web/src/views/apps/opsflow/components/canvas/DesignCanvas.vue` | 连接限制规则 + 回环边渲染 |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 机制 A Loop 配置区块 |

## 验证

1. **机制 A**：创建带 loop_config 的原子（ping_test loop_times=3），执行 → 验证执行 3 次，每次 IP 不同
2. **机制 B 画布**：从排他网关连接回前序节点 → 边以虚线橙色渲染，打开 ConditionDialog 可输入条件表达式
3. **机制 B 执行**：create → check → gateway(not_done→回 check, done→继续) → 验证循环直到条件满足
4. **混合**：同时含 A 和 B → 两者正常工作
5. **安全限制**：`max_iterations=100` 触发时正确失败
