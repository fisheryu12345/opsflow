# 移除执行回滚功能

> 提交: 4fbb2c87 | 日期: 2026-06-28
> 涉及 App: opsflow
> 类型: 重构

---

## 动机

流程引擎中存在三层 rollback 机制，其中"执行回滚"（即原子/节点执行失败后的补偿操作）经评估不再需要：

1. **执行回滚（已移除）** — 节点失败后调用 `Plugin.rollback()` 做补偿（如关闭已启动的 VM、删除已创建的实例）
2. **模板版本回滚（保留）** — 将流程模板恢复到历史版本（`TemplateVersionMixin.rollback()`）
3. **安全校验 / rollback 路径检查（保留）** — DAG 边 `failure`/`rollback` 标签用于路由校验

失败后行为：节点直接标记为 `failed`，**不做任何补偿操作**。

## 变更要点

### 核心引擎 `flow_engine.py`

| 变更前 | 变更后 |
|--------|--------|
| `_fail_execution(msg, save_fields, do_rollback=False)` — 含 `do_rollback` 参数 | `_fail_execution(msg, save_fields)` — 移除参数 |
| `rollback_failed_nodes()` — 遍历所有 failed 节点→`_trigger_plugin_rollback()` | ❌ 已删除 |
| `_trigger_plugin_rollback()` — 模块级函数，仅记录日志 | ❌ 已删除 |
| run() 中两处 `_fail_execution(..., do_rollback=True)` | `_fail_execution(...)` — 无 rollback 参数 |

`_fail_execution()` 简化后的签名：

```python
def _fail_execution(self, msg, save_fields=None):
    """标记执行为失败状态 — run() 中多处失败路径共享"""
    self.execution.status = "failed"
    self.execution.ended_at = timezone.now()
    if msg:
        self.execution.context['_validation_error'] = msg
    save_fields = save_fields or ["status", "ended_at"]
    if msg:
        save_fields.append("context")
    self.execution.save(update_fields=save_fields)
    self._notify_completed()
```

### 服务适配器 `plugin_service_adapter.py`

| 变更前 | 变更后 |
|--------|--------|
| `PluginService.rollback(data, parent_data)` — 从注册表查找插件实例并调用 `instance.rollback()` | ❌ 已删除 |

### 信号处理器 `signals/handlers.py`

`_handle_root_state_change()` 中 `FAILED` 分支：
- 之前：`engine.rollback_failed_nodes()` 自动触发回滚
- 之后：仅标记 failed + 保存 + Webhook，不再触发任何补偿

```python
# 变更前
elif target == PipelineState.FAILED:
    execution.status = PipelineState.FAILED
    execution.ended_at = timezone.now()
    _sweep_node_status(execution, "failed")
    execution.save(update_fields=["status", "ended_at", "node_status"])
    try:
        from opsflow.core.flow_engine import FlowEngine
        engine = FlowEngine(execution)
        engine.rollback_failed_nodes()
    except Exception:
        logger.exception(...)
    _try_webhook(execution, 'failed')

# 变更后
elif target == PipelineState.FAILED:
    execution.status = PipelineState.FAILED
    execution.ended_at = timezone.now()
    _sweep_node_status(execution, "failed")
    execution.save(update_fields=["status", "ended_at", "node_status"])
    _try_webhook(execution, 'failed')
```

### 插件层（14 个文件）

每个插件的 `rollback()` 方法被删除。所有插件的 rollback 实现模式一致：

```python
def rollback(self, context, **kwargs) -> dict:
    return {"success": True, "data": {}}
```

受影响插件：

| 插件组 | 插件 | rollback 行为（已删除） |
|--------|------|----------------------|
| ESXi (8) | power_on, power_off, create_snapshot, clone_vm, attach_disk, reboot, reconfigure_vm, revert_snapshot | 关机/开机/删快照/删克隆/no-op |
| 阿里云 ECS (4) | create_instance, stop_instance, start_instance, create_image | 释放实例/启停实例/删镜像 |
| Ansible Tower (1) | base_plugin | 取消 Tower 作业 |
| **BasePlugin** | base.py | 默认 no-op |

### 测试（1 个文件）

删除 `TestFlowEngineRollback` 类中的 3 个测试用例：
- `test_rollback_no_failed_nodes` — 无失败节点时不应调用 API
- `test_rollback_with_failed_nodes` — 失败节点触发 API 调用
- `test_rollback_handles_api_exception` — API 异常不应传播

同时修复所有 `test_flow_engine.py` 中的 mock 导入路径：`opsflow.core.flow_engine.pipeline_api` → `bamboo_engine.api`

## 设计决策

- **不保留 stub:** 既然不再需要执行回滚，不留空的 rollback 方法或日志桩，彻底删除让代码表达意图
- **保留模板版本回滚:** 该功能是"将模板恢复到历史版本"（类 git checkout），与执行补偿是完全不同的概念
- **保留 safety_guard rollback 路径校验:** DAG 边的 `failure`/`rollback` 标签用于节点路由，不是执行回滚
- **失败行为不做变更:** 保持直接标记 failed 的已有逻辑

## 关键文件

| 文件 | 说明 |
|------|------|
| `core/flow_engine.py` | FlowEngine — 移除 `rollback_failed_nodes()`、`_trigger_plugin_rollback()`、简化 `_fail_execution()` |
| `core/plugin_service_adapter.py` | PluginService — 移除 `rollback()` 方法 |
| `signals/handlers.py` | 信号处理器 — 移除 FAILED 分支中 rollback 触发 |
| `plugins/base.py` | BasePlugin — 移除默认 `rollback()` |
| `plugins/esxi/*.py` | 8 个 ESXi 插件 — 各删除 rollback() |
| `plugins/aliyun_ecs/*.py` | 4 个阿里云 ECS 插件 — 各删除 rollback() |
| `plugins/ansible/tower_backend/base_plugin.py` | Tower plugin — 删除 rollback() |
| `tests/test_flow_engine.py` | 删除 3 个 rollback 测试用例 |

## 验证

- `TestFlowEngineWSNotification` — ✅ 通过（2 tests OK）
- 全量测试 `python manage.py test opsflow` — 需确认无回归
- 安全校验（`safety_guard.py`）— 保持不变
- 模板版本回滚（`TemplateVersionMixin.rollback()`）— 保持不变

### 关联文档

- 相关设计文档: [2026-06-28-remove-execution-rollback-design.md](../../superpowers/specs/2026-06-28-remove-execution-rollback-design.md)
