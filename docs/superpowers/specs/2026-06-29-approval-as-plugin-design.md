# Approval 原子重构 — 从特殊节点到标准插件

> 版本: 1.0 | 日期: 2026-06-29 | 状态: 已批准

---

## 1. 概述

将现有的 approval 节点从 elements.py 中的特殊分支 + 信号处理器检测 + 未知插件 ERROR 的弯绕架构，重构为一个标准的 `ApprovalPlugin`，与 manual_pause 采用相同模式——PluginService 直接触发暂停，前端通过 `_pause_reason` 区分暂停类型。

### 目标

- ApprovalPlugin 注册为标准插件（`plugins/approval/approval.py`），自动发现
- Form schema 提供人员选择器（async_select，多选，搜索用户）
- execute() 返回成功，PluginService 直接调用 FlowEngine.pause()
- 删除 elements.py 中的 approval 特殊分支、_is_approval_node()、trace.py 中的审批暂停分支
- 前端通过 `context._pause_reason === 'approval'` 判断，不再依赖 `_is_approval_node` API 调用
- 保留 approve/reject API、审批中心页面、审批 banner 交互

---

## 2. 架构

### 执行流

```
用户拖入 Approval 原子 → 选择审批人 → 保存

执行时:
  → bamboo-engine 执行 ServiceActivity(opsflow_plugin, _atom_type=approval)
  → PluginService.execute() 检测到 _atom_type == 'approval'
  → 校验 approvers 非空
  → 写入 context._pause_reason = 'approval'
  → 写入 context._approvers
  → FlowEngine(execution).pause()
  → return True  (节点成功完成，无 ERROR 日志)
  → 前端轮询发现 status='paused' + _pause_reason='approval'
  → 显示审批 banner（Approve + Reject 按钮）
  → 用户点击 Approve/Reject
  → POST /api/opsflow/executions/{id}/approve/ 或 reject/
  → FlowEngine(execution).resume()
  → 流程继续
```

### 对比（重构前 vs 重构后）

```
重构前:
  elements.py 特殊 approval 分支 → get_plugin 找不到 → 未知插件 ERROR
  → execute() 返回 False → schedule() 处理 → FINISHED → 信号处理器 _is_approval_node()
  → pause (信号漏发则无法暂停)

重构后:
  ApprovalPlugin 正常注册 → get_plugin 找到 → execute() 返回成功
  → PluginService 直接 pause (同 manual_pause 模式)
  → 节点 FINISHED → 流程正常继续 (无 ERROR 日志)
```

---

## 3. 详细设计

### 3.1 ApprovalPlugin

**文件:** `backend/opsflow/plugins/approval/approval.py`（新建目录 `plugins/approval/`）

```python
class ApprovalPlugin(BasePlugin):
    name = "审批"
    name_en = "Approval"
    code = "approval"
    group = "流程控制"
    description = "暂停流程并等待指定审批人审批"
    description_en = "Pause and wait for specified approvers"
    risk_level = "low"
    icon = "Clock"
    color = "#9B59B6"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="approvers",
                type="async_select",
                name="审批人",
                name_en="Approvers",
                attrs={
                    "api": "/api/iam/users/search",
                    "multiple": True,
                    "placeholder": "搜索并选择审批人",
                },
                validation=[ValidationRule(type="required")],
            ),
        ]

    def execute(self, approvers=None, **kwargs):
        if not approvers:
            return {"success": False, "error": "请选择审批人"}
        # 暂停由 PluginService 处理，这里只做参数校验
        return {"success": True, "data": {"approvers": approvers}}
```

### 3.2 PluginService 处理

**文件:** `backend/opsflow/core/plugin_service_adapter.py`

在 manual_pause 分支之后追加 approval 分支：

```python
if atom_type == 'manual_pause':
    ...现有代码...

if atom_type == 'approval':
    from opsflow.core.flow_engine import FlowEngine
    from opsflow.models import FlowExecution
    try:
        execution = FlowExecution.objects.get(id=_execution_id)
        execution.context['_pause_reason'] = 'approval'
        execution.context['_approvers'] = params.get('approvers', [])
        execution.save(update_fields=['context'])
        FlowEngine(execution).pause()
        logger.info("[Approval] Node paused execution %s (approval)", _execution_id)
    except Exception:
        logger.exception("[Approval] pause failed")
    data.outputs['_result'] = True
    return True
```

### 3.3 删除旧代码

| 文件 | 行 | 操作 |
|------|----|------|
| `core/pipeline_builder/elements.py` | 170-177 | 删除整个 `approval` 特殊分支 |
| `signals/helpers.py` | 52-63 | 删除整个 `_is_approval_node()` 函数 |
| `signals/trace.py` | 头文件 import | 删除 `_is_approval_node` 导入 |
| `signals/trace.py` | 89-97 | 删除 approval pause 分支 |

### 3.4 前端 ExecutionDetail.vue

改为通过 `_pause_reason` 区分暂停类型：

```typescript
const isApprovalPause = computed(() => 
  execDetail.value.status === 'paused' && execDetail.value.context?._pause_reason === 'approval'
)
const isPendingApproval = computed(() => isApprovalPause.value)
const isManualPause = computed(() => 
  execDetail.value.status === 'paused' && execDetail.value.context?._pause_reason === 'manual_pause'
)
```

审批 banner 条件简化为 `v-if="isPendingApproval"`。

### 3.5 保留不变

- `opsflow-approval/index.vue` — 审批中心页面
- `execution_approval.py` Mixin — approve/reject API
- `ExecutionList.vue` — pending_approval 过滤
- `MonitorCanvas.vue` — pending_approval 着色
- `states.py` — PENDING_APPROVAL 状态枚举
- `execution.py` Model — PENDING_APPROVAL 状态选择

---

## 4. 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/opsflow/plugins/approval/__init__.py` | **新建** | 空 init |
| `backend/opsflow/plugins/approval/approval.py` | **新建** | ApprovalPlugin，async_select 人员选择器 |
| `backend/opsflow/core/plugin_service_adapter.py` | 修改 | 追加 approval 分支（直接 pause） |
| `backend/opsflow/core/pipeline_builder/elements.py` | 修改 | 删除 approval 特殊分支 |
| `backend/opsflow/signals/helpers.py` | 修改 | 删除 `_is_approval_node()` |
| `backend/opsflow/signals/trace.py` | 修改 | 删除 import + approval pause 分支 |
| `web/src/views/apps/opsflow-execution/components/ExecutionDetail.vue` | 修改 | `_pause_reason` 判断取代 `_is_approval_node` |
| `backend/opsflow/tests/test_manual_pause.py` | 修改 | 测试不引用已删除的 `_is_approval_node` |

---

## 5. 不清理的理由

以下内容虽然与 approval 相关，但属于**跨功能公用的基础设施**，不做清理：

- `states.py` — `PENDING_APPROVAL` 状态枚举被前端多处引用
- `execution.py` — `pending_approval` status option 被前端和 portal 引用
- `audit.py` — `APPROVE`/`REJECT` 是通用的审计操作类型
- `error_codes.py` — `APPROVAL_*` 错误码保留兼容
- `execution_approval.py` — 复用现有 approve/reject API 逻辑
- `opsflow-approval/` 前端页面 — 审批中心保留

---

## 6. 测试计划

| 测试 | 类型 | 断言 |
|------|------|------|
| ApprovalPlugin.execute() 空参数返回失败 | 单元 | `result['success'] is False` |
| ApprovalPlugin.execute() 有参数返回成功 | 单元 | `result['success'] is True` |
| ApprovalPlugin.get_form_config() 含 approvers | 单元 | `type == 'async_select'` |
| PluginService 执行 approval 触发 pause | 集成 | `FlowEngine.pause` called |
| 审批流程端到端: pause → approve → resume | E2E | status 流转 |
