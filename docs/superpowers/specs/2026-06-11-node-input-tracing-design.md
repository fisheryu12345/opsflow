# Node Input Tracing — 节点执行入参追踪

> **日期:** 2026-06-11
> **状态:** 设计已批准

---

## 1. 现状

前端 ExecutionDetail.vue 的 Data tab 已有 Inputs/Outputs 两栏：

```
Data Tab
├─ Inputs    ← 显示 "No data"（trace.inputs 始终为 {}）
├─ Outputs   ← 正常显示（trace.outputs 由 _capture_node_outputs 写入）
└─ stdout
```

- `NodeExecutionTrace` 模型已有 `inputs` 字段（`JSONField`）
- `NodeExecutionTraceSerializer` 已包含 inputs
- 前端 `nodeInputs` 变量已从 `t.inputs` 读取
- **唯一缺口：没有代码往 `trace.inputs` 写数据**

## 2. Bamboo-engine 原生能力

引擎提供 `get_execution_data_inputs()` API，直接读取节点执行时的入参（SPLICE 已解析）：

```python
api.get_execution_data_inputs(runtime, node_id).data
# → {'_loop': 1, 'command': 'df -h', 'host': '10.0.0.1', '_atom_type': 'shell', ...}
```

与 `_capture_node_outputs` 不同，inputs 不需要用 `execution.context._node_outputs` 兜底：
- **outputs：** 信号触发时 ERI 尚未持久化 → 从 context 取
- **inputs：** 节点 execute() **之前**已完成 SPLICE 解析并写入 ERI → 原生 API 可直接读

## 3. 改动

### 3.1 后端：`signals/trace.py`

新增一个函数，在 `_record_node_trace()` 中调用：

```python
def _capture_node_inputs(execution, node_id, runtime) -> dict:
    """从 bamboo-engine ERI 读取节点执行输入（SPLICE 已解析后的值）"""
    try:
        from bamboo_engine import api as pipeline_api
        result = pipeline_api.get_execution_data_inputs(runtime, node_id)
        if result.result and result.data:
            # 过滤 _ 开头的内部字段（_loop/_atom_type/_execution_id 等）
            return {k: v for k, v in result.data.items() if not k.startswith('_')}
    except Exception:
        logger.exception("[Signal] _capture_node_inputs failed")
    return {}
```

在 `_record_node_trace` 的 FINISHED/FAILED 分支中加一行：

```python
if to_state in (states.FINISHED, states.FAILED):
    trace.outputs = _capture_node_outputs(execution, node_id)
    trace.inputs = _capture_node_inputs(execution, node_id, BambooDjangoRuntime())  # ← 新增
    trace.save()
```

### 3.2 前端：无需改动

| 前端组件 | 状态 |
|---------|------|
| `Data tab` | ✅ 已有 Inputs 栏 |
| `nodeInputs` 变量 | ✅ 已从 `trace.inputs` 读取 |
| `formatDataValue()` | ✅ 已能格式化展示 |
| 翻译 | ✅ 已存在 |

## 4. 涉及文件

| 文件 | 改动量 | 说明 |
|------|--------|------|
| `opsflow/signals/trace.py` | ~15 行 | 新增 `_capture_node_inputs()` + 调用 |
| 前端 | 0 行 | 已有能力 |

## 5. 验证

1. `python manage.py check`
2. 执行一个包含 shell/CMDB 等插件的 pipeline
3. 前端点击已完成节点 → Data tab 显示 Inputs（如 `{command: "df -h", host: "10.0.0.1"}`）
4. 确认 `_` 开头的内部字段被过滤（不显示 `_loop`、`_atom_type` 等）
