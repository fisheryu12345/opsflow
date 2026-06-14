# 运行时 `${node_id.field}` 变量解析修复

> 提交: ad7c550c | 日期: 2026-06-14
> 类型: fix

---

## 问题

运行时 `${c1}${node_1.test1}` 中 `$c1` 正确解析为 `1111`，但 `${node_1.test1}` 保持字面值未解析。

## 根因

bamboo-engine 的 `NodeOutput` 注册到 `data.inputs` 时 `value=None`：

```python
class NodeOutput(Var):
    def __init__(self, ...):
        kwargs["value"] = None  # 永远为 None
```

引擎运行时创建 `SpliceVariable("${node_1.test1}", None, context)` → `ConstantTemplate(None).get_reference()` 返回空列表 → 不构建引用 → 不解析。

而 `$c1` 注册为 `Var(PLAIN, "1111")` → `PlainVariable.get()` 直接返回值 → 正确解析。

## 方案

在 `PluginService.execute()` 中，bamboo-engine 完成 SPLICE 解析后，对仍含 `${` 的参数做二次解析：

```python
# backend/opsflow/core/plugin_service_adapter.py
if _execution_id:
    try:
        from opsflow.models import FlowExecution
        from opsflow.core.variable_resolver import build_execution_context, resolve_variables
        execution = FlowExecution.objects.get(id=_execution_id)
        ctx = build_execution_context(execution)
        for k, v in list(resolved_params.items()):
            if isinstance(v, str) and '${' in v:
                resolved = resolve_variables(v, ctx)
                if resolved != v:
                    resolved_params[k] = resolved
    except Exception:
        logger.exception("二次变量解析失败")
```

`build_execution_context()` 从 `NodeExecutionTrace`（已完成节点）读取 outputs，注入到 `ctx[nid] = outputs`，`resolve_variables()` 按 `${nid.field}` 点号查找。

## Data Flow

```
PluginService.execute()
  → bamboo-engine SPLICE: $c1 → "1111"  ✅,  ${node_1.test1} → 保持  ❌
  → 二次解析: resolve_variables(v, build_execution_context(execution))
    → build_execution_context() 查询 NodeExecutionTrace(execution, status=completed)
    → ctx = {"c1": "1111", "node_1": {"test1": 7, ...}}
    → resolve_variables("${c1}${node_1.test1}", ctx)
    → 正则匹配 ${c1} → "1111", ${node_1.test1} → ctx["node_1"]["test1"] = "7"
    → "11117" ✅
  → plugin_cls().execute(message="11117")
```

## 验证

输入 `${c1}${node_1.test1}` → 输出 `11117`（需重启 Django 后执行）

### 关联文档

- 相关调试记录: [node-output-variable-fixes.md](debug/2026-06-14-node-output-variable-fixes.md)
