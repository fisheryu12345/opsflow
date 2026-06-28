# 移除执行回滚功能设计文档

> **日期:** 2026-06-28
> **状态:** 已批准
> **范围:** 仅移除执行回滚（类型 ①），保留模板版本回滚和安全校验

## 背景

流程引擎中目前存在三层 rollback 机制，经过评估确定"执行回滚"功能不再需要：

1. **执行回滚（本 spec 焦点）** — 原子/节点执行失败后调用 Plugin.rollback() 做补偿操作
2. 模板版本回滚 — 保留（恢复到历史版本，不同概念）
3. 安全校验 / rollback 路径检查 — 保留（DAG 边的 `failure`/`rollback` 标签用于路由）

失败后行为：节点标记为 `failed`，不做任何补偿操作。

## 改动范围

### 一、插件层（14 个文件）

移除每个插件中的 `rollback()` 方法定义。所有插件 rollback 模式一致：

```python
def rollback(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """回滚操作（可选覆盖）"""
    return {"success": True, "data": {}}
```

#### BasePlugin 基类

**文件:** `backend/opsflow/plugins/base.py`

- 删除 `rollback()` 方法定义（不再提供默认实现）

#### ESXi 插件（8 个文件）

| 文件 | 当前 rollback 行为 |
|------|-------------------|
| `plugins/esxi/power_on.py` | power off（关闭虚拟机） |
| `plugins/esxi/power_off.py` | power on（启动虚拟机） |
| `plugins/esxi/create_snapshot.py` | 删除刚创建的快照 |
| `plugins/esxi/clone_vm.py` | 删除克隆出的虚拟机 |
| `plugins/esxi/attach_disk.py` | no-op（无法自动卸载） |
| `plugins/esxi/reboot.py` | no-op（重启不可逆） |
| `plugins/esxi/reconfigure_vm.py` | no-op（无法自动回滚配置） |
| `plugins/esxi/revert_snapshot.py` | no-op（快照恢复不可逆） |

#### 阿里云 ECS 插件（4 个文件）

| 文件 | 当前 rollback 行为 |
|------|-------------------|
| `plugins/aliyun_ecs/create_instance.py` | 释放刚创建的实例 |
| `plugins/aliyun_ecs/stop_instance.py` | 启动实例 |
| `plugins/aliyun_ecs/start_instance.py` | 停止实例 |
| `plugins/aliyun_ecs/create_image.py` | 删除镜像 |

#### Ansible Tower 插件（1 个文件）

| 文件 | 当前 rollback 行为 |
|------|-------------------|
| `plugins/ansible/tower_backend/base_plugin.py` | 取消 Tower 作业 |

#### 删除模式

每个文件中的删除操作一致：
1. 定位 `def rollback(self, ...)` 方法
2. 删除整个方法（含 docstring 和 body）
3. 如果该方法后有空行，保留一个空行

### 二、核心服务层（3 个文件）

#### `core/flow_engine.py`

| 改动项 | 说明 |
|--------|------|
| 删除 `rollback_failed_nodes()` | 整个方法（约 23 行） |
| 删除 `_trigger_plugin_rollback()` | 模块级函数（约 6 行） |
| `_fail_execution()` 简化 | 移除 `do_rollback` 参数 |
| `run()` 中调用 | 两处 `_fail_execution(do_rollback=True)` → `_fail_execution()` |
| import 清理 | 检查 `pipeline_api.get_execution_data_outputs` 是否只有 rollback 在使用 |

简化后的 `_fail_execution()` 签名：

```python
def _fail_execution(self, msg, save_fields=None):
    """标记 execution 为 failed"""
    self.execution.status = "failed"
    if save_fields:
        save_fields = list(set(save_fields + ["status"]))
        self.execution.save(update_fields=save_fields)
    else:
        self.execution.save()
    self._notify_completed()
```

#### `core/plugin_service_adapter.py`

- 删除 `PluginService.rollback()` 方法（约 14 行）

#### `signals/handlers.py`

- 删除 `_handle_root_state_change()` 中 `FAILED` 分支的 rollback 触发块（约 9 行）

改动后的 FAILED 分支：

```python
elif target == PipelineState.FAILED:
    execution.status = PipelineState.FAILED
    execution.ended_at = timezone.now()
    _sweep_node_status(execution, "failed")
    execution.save(update_fields=["status", "ended_at", "node_status"])
    # rollback 触发已移除
```

### 三、测试层（1 个文件）

#### `tests/test_flow_engine.py`

移除 3 个 rollback 测试用例（`test_rollback_no_failed_nodes`、`test_rollback_with_failed_nodes`、`test_rollback_handles_api_exception`）。

同时检查 Mock/import 中是否有仅被 rollback 测试使用的部分需清理。

### 四、保持不变的代码

| 代码 | 原因 |
|------|------|
| `TemplateVersionMixin.rollback()` | 模板版本回滚（恢复历史版本）|
| `VersionDialog.vue` | 模板版本回滚 UI |
| `RollbackTemplate` API function | 模板版本回滚 API 调用 |
| i18n 字符串中的 "rollback/回滚" | 模板版本回滚相关 |
| `safety_guard.py` rollback 路径检查 | DAG 边标签校验，不影响功能 |
| `OperationRecord.Action.ROLLBACK` | 模板版本回滚审计使用 |
| seed 数据 "回滚方案" | 仅方案名称标签 |
| LLM service 中 rollback 路径提示 | 安全校验一部分 |

## 影响分析

### 正向影响
- 减少 ~290 行代码
- 简化 14 个插件类（每个减少一个方法）
- 简化 FlowEngine 接口（减少一个公共方法）
- 移除信号处理器中的副作用逻辑

### 无影响
- 数据库 schema 无变化（无 rollback 相关 model 字段）
- API 路由无变化（模板版本回滚 API 保留）
- 前端无变化
- 现有 execution 记录的状态不受影响

## 验证方案

1. **测试执行：** `python manage.py test opsflow.tests.test_flow_engine`
   - 确认 rollback 测试用例已移除
   - 确认其他测试用例全部通过
2. **全量测试：** `python manage.py test opsflow` — 无回归
3. **编译检查：** `python -m py_compile` 或 `import` 检查无 import 残留
4. **CI 检查：** 确认 git diff 只包含目标文件的 rollback 删除

## 实现计划

### Phase 1: 核心服务层清理（3 个文件）
1. `core/flow_engine.py` — 删除 rollback_failed_nodes、_trigger_plugin_rollback、简化 _fail_execution
2. `core/plugin_service_adapter.py` — 删除 PluginService.rollback()
3. `signals/handlers.py` — 删除 rollback 触发块

### Phase 2: 插件层清理（14 个文件）
4. `plugins/base.py` — 删除基类 rollback()
5. 逐个清理 13 个插件的 rollback() 方法

### Phase 3: 测试清理
6. `tests/test_flow_engine.py` — 删除 rollback 测试用例

### Phase 4: 验证
7. 运行测试、检查 import 残留
