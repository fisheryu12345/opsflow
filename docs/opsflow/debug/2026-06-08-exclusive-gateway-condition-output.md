# 排他网关条件评估与节点输出显示调试全记录

> 最后更新: 2026-06-08
> 涉及版本: commit `24691761`
> 涉及 App: opsflow

---

## 1. 背景与现象

排他网关（Exclusive Gateway）执行时，条件表达式引用前面节点的输出变量（如 `${n1.test1 >= 5}`），但：

1. **条件不命中** — 排他网关始终走默认分支，自定义条件从不匹配，因为条件变量未正确注入到 bamboo-engine 的 `ContextValue` 表
2. **节点输出不显示** — 执行详情页（trace）中 node 的 `outputs` 字段为空，用户看不到节点执行后的输出值
3. **条件编辑器变量列表不完整** — 前端条件编辑器下拉列表中，可用变量格式为 `_result (boolean)`，缺少节点名前缀（应为 `n1._result (boolean)`），且部分插件的输出字段未出现在下拉列表中

**错误日志（调试中发现）：**
```log
[Signal] get_execution_data_outputs failed for node n5
# 信号触发时 get_execution_data_outputs 返回空，trace outputs 一直为空
```

---

## 2. 排查思路

### 2.1 信号时序分析

跟踪 `_capture_node_outputs` 发现其通过 `bamboo_engine.api.get_execution_data_outputs()` 读取节点输出。但 bamboo-engine 的信号触发顺序是：

```
on_post_set_state 信号触发
    │
    ▼
_signal_handler（我们的代码）调用 _capture_node_outputs  ← ⚠ 此时 outputs 尚未持久化
    │
    ▼
set_execution_data 回调（bamboo-engine 内部）             ← outputs 在此之后才写入 DB
```

因此 `get_execution_data_outputs()` 总返回空数据，这是一个**时序竞态**问题。

### 2.2 条件变量注入路径分析

原有的 `_promote_result` 函数仅将一个布尔值 `_result` 写入 `ContextValue` 表：

```python
runtime.upsert_plain_context_values(bamboo_pipeline_id, {
    "_result": ContextValue(key="_result", type=ContextValueType.PLAIN, value=result_value),
})
```

而排他网关条件如 `${n1.test1 >= 5}` 需要的是具体的变量值（如 `test1` 的数值），不是 `_result`。bamboo-engine 的条件评估器从 `ContextValue` 表中按 key 查找 `${}` 引用的变量，找不到则条件判定为 `False`。

### 2.3 变量注入 key 格式问题

`build_bamboo_pipeline` 中的 `_build_data_inputs` 对 `auto_vars` 做了 `${}` 包裹：

```python
wrapped_name = f"${{{var_name}}}"  # 如 ${_result_n1}
data.inputs[wrapped_name] = NodeOutput(...)
```

但 `variable_resolver` 在 pipeline 执行时解析 `${var}` 语法，存储时 key 已经带 `${}`，导致变量解析时找不到匹配 — 多了一层包裹。

### 2.4 前端变量下拉列表分析

`getAvailableVars` 返回的变量格式为 `field_key (field_type)`，如 `_result (boolean)`，没有节点 ID 前缀。当画布上有多个节点时，用户无法区分变量来自哪个节点。同时 PropertyPanel 无法直接获取 graph 实例，导致 `extractAvailableVariables(nodes, store)` 中的 `nodes` 始终为空数组。

---

## 3. 根因分析

本问题由**两个独立但关联的缺陷**叠加导致：

### 时序缺陷（输出不显示）

```
PluginService.execute 结束
    │
    ├──▶ bamboo-engine 触发 on_post_set_state
    │       │
    │       └──▶ _capture_node_outputs 调用 get_execution_data_outputs → ❌ 空数据
    │
    └──▶ bamboo-engine 内部 set_execution_data 写入 outputs → ✅ 数据就绪
```

bamboo-engine 的信号 `on_post_set_state` 触发在 `set_execution_data` **之前**，而 `_capture_node_outputs` 恰好在信号处理中调用。这是 bamboo-engine 框架层的行为，无法通过调整调用顺序修复。

### 数据注入缺陷（条件不命中）

1. `_promote_result` 仅注入 `_result` 布尔值，不注入插件输出的具体变量
2. NodeOutput 变量 key 被多包裹一层 `${}`，导致 `variable_resolver` 找不到匹配
3. `build_bamboo_pipeline` 没有将 `auto_vars` 映射返回给 `FlowEngine`，执行上下文不知道哪些变量是自动生成的

### 前端显示缺陷

4. PropertyPanel 缺少 graph 实例引用，条件编辑器拿不到节点列表
5. 变量下拉列表不显示节点 ID 前缀，多节点场景下变量归属不明
6. 边 label 在编辑后未持久化，刷新后自定义标签丢失

---

## 4. 解决方案

### 4.1 `backend/opsflow/core/plugin_service_adapter.py`

- **改动：** 重写 `_promote_result` → `_promote_results(result_value, output_fields, execution_id, node_id)`
- **目的：** 新函数做两件事：
  1. 遍历 `auto_vars` 映射，将当前节点产生的输出字段按 `${var_name}` 格式写入 `ContextValue` 表，供排他网关条件评估
  2. 将完整 `output_fields` 写入 `execution.context['_node_outputs'][node_id]`，供 trace 读取

**关键逻辑：**
```python
# 1. 条件变量注入 — 只注入属于当前节点的 auto_vars
for var_name, spec in auto_vars.items():
    source_key = spec.get('source_key', '')
    if spec.get('source_act') == node_id and source_key in output_fields:
        ref_key = "${%s}" % var_name
        cv_map[ref_key] = ContextValue(key=ref_key, type=ContextValueType.PLAIN, value=output_fields[source_key])

# 2. 节点输出持久化到 execution.context
node_outputs[_nid] = dict(output_fields)
node_outputs[_nid]['_result'] = result_value
ctx['_node_outputs'] = node_outputs
execution.context = ctx
execution.save(update_fields=['context'])
```

- **改动：** `PluginService.execute` 中从 `data.inputs['_execution_id']` 获取执行 ID（而非从 `parent_data` 获取）
- **目的：** `_execution_id` 现在由 `_create_element` 注入到每个节点的 inputs 中，解除了对 `parent_data` 的依赖

- **改动：** 将插件返回的 `executor_output` 字段提升到 `data.outputs` 顶层
- **目的：** 条件表达式 `${node_id.field_name}` 能直接引用插件输出字段

### 4.2 `backend/opsflow/signals/trace.py`

- **改动：** `_capture_node_outputs` 从 `execution.context['_node_outputs']` 读取，不再调用 `get_execution_data_outputs`
- **目的：** 避开 bamboo-engine 的信号时序问题 — `_promote_results` 在 `execute()` 中同步写入 context，此时数据已就绪

- **改动：** `_log_node_result` 复用 `_capture_node_outputs` 来获取 outputs
- **目的：** 统一输出获取方式，删除重复的 `get_execution_data_outputs` 调用代码

### 4.3 `backend/opsflow/core/pipeline_builder/__init__.py`

- **改动：** `build_bamboo_pipeline` 返回 `(pipeline, auto_vars)` 而非 `(pipeline, {})`
- **目的：** `FlowEngine` 拿到 `auto_vars` 映射，存入 execution context，后续 `_promote_results` 才能遍历该映射并正确注入条件变量

- **改动：** `_build_data_inputs` 中 NodeOutput 的 key 不再加 `${}` 包裹
- **目的：** 修复 `variable_resolver` 找不到变量的问题

### 4.4 `backend/opsflow/core/pipeline_builder/elements.py`

- **改动：** `_create_element` 接收 `execution_id` 参数，注入到 `act.component.inputs['_execution_id']`
- **目的：** 每个插件节点运行时都能拿到执行 ID，不再需要从 `parent_data` 解析

### 4.5 `backend/opsflow/core/flow_engine.py`

- **改动：** 接收 `build_bamboo_pipeline` 返回的 `auto_vars`，存入 `execution.context["auto_vars"]`
- **目的：** 持久化自动变量映射，供后续 `_promote_results` 使用

### 4.6 `backend/opsflow/plugins/common/test_print_time.py`

- **改动：** 添加 `test1 = random.randint(1, 10)` 随机输出和 `get_output_schema()` 类方法
- **目的：** 为排他网关条件测试提供一个可引用的输出变量（如 `${n1.test1 >= 5}`）

### 4.7 `backend/opsflow/serializers.py` + `backend/opsflow/core/node_dispatcher.py`

- **改动：** `get_trace_summary` 和 `get_trace` 查询包含 `outputs` 字段
- **目的：** API 返回节点输出数据，供前端展示

### 4.8 `web/src/views/apps/opsflow/composables/useGraphCanvas.ts`

- **改动：** 条件变量下拉格式改为 `node_id.field_key (field_type)`（如 `n1.test1 (number)`）
- **目的：** 用户能清楚区分不同节点的同名变量

- **改动：** 添加 `atomDefaults` 映射，按原子类型返回输出字段兜底
- **目的：** 插件 `output_schema` 未同步到前端时，条件编辑器仍能显示正确字段列表

### 4.9 `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue`

- **改动：** 接收 `getGraphData` prop，在 `openConditionDialog` 中实时获取画布节点列表
- **目的：** 条件编辑器可用变量列表不再为空

### 4.10 `web/src/views/apps/opsflow/components/canvas/DesignCanvas.vue`

- **改动：** 传入 `getGraphData` 给 PropertyPanel；边 label 持久化到 edgeData
- **目的：** PropertyPanel 能获取 graph 引用；刷新后边 label 不丢失

### 4.11 `backend/application/settings.py`

- **改动：** `apscheduler.executors.default` 日志级别降为 `WARNING`
- **目的：** 减少 APScheduler 的 INFO 日志噪音

---

## 5. 引入的方法 / 函数 / 设计模式

| 引入内容 | 所在文件 | 说明 |
|---------|---------|------|
| `_promote_results()` | `plugin_service_adapter.py` | 替代原 `_promote_result`，同时支持条件变量注入 + output 持久化 |
| `get_output_schema()` | `test_print_time.py` | 插件类方法声明输出字段 schema，供条件编辑器动态获取 |
| `atomDefaults` | `useGraphCanvas.ts` | 原子类型→输出字段的兜底映射，schema 未同步时使用 |
| `auto_vars` 全链路传递 | `flow_engine.py` → `pipeline_builder/__init__.py` → `plugin_service_adapter.py` | 从构建时到运行时持久化 `auto_vars` 映射的完整链路 |
| `execution.context['_node_outputs']` | `plugin_service_adapter.py` + `signals/trace.py` | 绕过 bamboo-engine 时序问题的节点输出承载机制 |

---

## 6. 验证

1. **条件评估测试：** 创建流程：打印时间节点（`test_print_time`）→ 排他网关（条件 `${n1.test1 >= 5}` → 高分支，否则 → 低分支）。多次执行观察分支命中情况
2. **输出显示测试：** 执行完成后，查看节点详情（trace）的 outputs 字段，确认包含 `test1`、`timestamp`、`message`、`sleep_seconds` 等插件输出
3. **条件编辑器测试：** 编辑排他网关后的边条件，下拉列表中应显示 `n1.test1 (number)`、`n1.timestamp (string)` 等格式的变量
4. **边 label 持久化测试：** 编辑边 label 后保存流程，刷新页面确认 label 不丢失
5. **APScheduler 日志验证：** 确认控制台不再输出大量的 `apscheduler.executors.default` INFO 日志

---

## 7. 涉及文件清单

| 文件路径 | 改动概述 |
|---------|---------|
| `backend/opsflow/core/plugin_service_adapter.py` | 重写 `_promote_result` → `_promote_results`，支持条件变量注入 + output 持久化 |
| `backend/opsflow/signals/trace.py` | `_capture_node_outputs` 改从 `execution.context` 读取，绕过 bamboo-engine 时序问题 |
| `backend/opsflow/core/pipeline_builder/__init__.py` | `build_bamboo_pipeline` 返回 `auto_vars`；修复 NodeOutput key 格式 |
| `backend/opsflow/core/pipeline_builder/elements.py` | `_create_element` 注入 `_execution_id` 到节点 inputs |
| `backend/opsflow/core/flow_engine.py` | 接收 `auto_vars` 并存入 execution.context |
| `backend/opsflow/serializers.py` | `get_trace_summary` 包含 `outputs` 字段 |
| `backend/opsflow/core/node_dispatcher.py` | `get_trace` 查询包含 `outputs` 字段 |
| `backend/opsflow/plugins/common/test_print_time.py` | 添加 `test1` 随机输出和 `get_output_schema()` |
| `backend/application/settings.py` | apscheduler 日志降级到 WARNING |
| `web/src/views/apps/opsflow/composables/useGraphCanvas.ts` | 变量下拉显示 `node.field_name`；添加 `atomDefaults` 兜底 |
| `web/src/views/apps/opsflow/composables/useDesignCanvas.ts` | 边 label 持久化到 edgeData |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 接收 `getGraphData` prop，刷新可用变量列表 |
| `web/src/views/apps/opsflow/components/canvas/DesignCanvas.vue` | 传入 `getGraphData`；边 label 持久化 |
