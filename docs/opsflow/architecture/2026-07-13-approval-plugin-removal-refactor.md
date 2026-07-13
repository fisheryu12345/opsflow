# OpsFlow Approval Plugin 移除 — 审批统一走 ITSM

> 提交: 88c59d27 | 日期: 2026-07-13
> 涉及 App: opsflow + iam
> 类型: 重构

---

## 动机

OpsFlow 原有的 Approval 节点（审批原子）是一个轻量实现：Pipeline 执行到 approval 节点时暂停，等待用户在 OpsFlow 审批中心通过/拒绝。然而该功能与 ITSM 的审批流程功能重叠，且 ITSM 已具备完整的工单审批、委托、SLA 等能力。为消除重复、统一审批体验，决定：

1. **移除 OpsFlow 审批插件** — ApprovalPlugin、审批中心前端、i18n 键
2. **移除 ITSM-OpsFlow 旧版触发集成** — `opsflow_trigger.py` 中基于 `TicketOpsflowConfig` 的审批后触发已被 `ItsmAutoTaskService` 替代
3. **移除 OpsFlow TriggerAction 中的 OPSFLOW 类型** — ITSM 触发器不再支持直接触发 OpsFlow（改用自动任务节点）
4. **SubmitWizardDialog 改用真实 ITSM 变更工单** — 此前使用 mock ServiceNow API，现直接查询 ITSM change 工单

## 变更要点

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `backend/opsflow/plugins/approval/approval.py` | ApprovalPlugin 标准插件实现 | 删除 |
| `backend/opsflow/plugins/approval/__init__.py` | 插件包声明 | 删除 |
| `backend/opsflow/core/plugin_service_adapter.py` | `atom_type == 'approval'` 特殊处理 — 暂停 execution 并写入 `_pause_reason` / `_approvers` | 删除该分支 |
| `backend/opsflow/management/commands/seed_opsflow.py` | `SAMPLE_PLUGINS` 含 `"Wait for Approval"` | 移除 |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 注册 `opsflow:approvals:view` 权限 | 移除 |
| `backend/iam/migrations/0003_remove_opsflow_approvals_tab.py` | — | 新增数据迁移，删除 `PageTab`(approvals) 和 `IAMPermission`(approvals:view) |
| `backend/itsm/services/opsflow_trigger.py` | `TicketOpsflowConfig` 模型 + `OpsflowTriggerService` 服务 | 删除（被 `ItsmAutoTaskService` 替代） |
| `backend/itsm/models/trigger.py` | `TriggerAction.ACTION_TYPE_CHOICES` 含 `('OPSFLOW', '触发运维流程')` | 移除该选项 |
| `backend/itsm/services/trigger_service.py` | `OpsflowRunner` 处理 OPSFLOW action | 删除 |
| `backend/itsm/views/ticket_views.py` | 审批通过后调用 `OpsflowTriggerService.on_ticket_approved()` | 移除 |
| `web/src/views/apps/opsflow-approval/index.vue` | 审批中心页面（待审批列表、通过/拒绝操作） | 删除 |
| `web/src/views/apps/opsflow/index.vue` | 注册 `approvals` tab 并 import `OpsflowApproval` | 移除 |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | `isApproval` 分支：审批人选择、超时配置 + 加载用户列表 | 删除 |
| `web/src/views/apps/opsflow/components/common/HelpDrawer.vue` | approval 节点帮助说明 | 删除 |
| `web/src/views/apps/opsflow/composables/useGraphCanvas.ts` | `defaultNodeLabel()` 含 `approval` 映射 | 删除 |
| `web/src/views/apps/opsflow/api/executions.ts` | `GetPendingApprovals()` API | 删除 |
| `web/src/i18n/pages/opsflow/en.ts` | ~25 个 approval 相关翻译键 | 删除 |
| `web/src/i18n/pages/opsflow/zh-cn.ts` | ~25 个 approval 相关翻译键 | 删除 |
| `web/src/views/apps/itsm/designer/components/TriggerConfigSection.vue` | OPSFLOW action 类型支持 | 移除 |
| `docs/itsm/implementation.md` | OpsFlow 集成描述为旧版 | 更新为 ItsmAutoTaskService |

### 代码对比

**重构前** — PluginService 中 approval 特殊处理：

```python
# backend/opsflow/core/plugin_service_adapter.py (删除)
if atom_type == 'approval':
    from opsflow.core.flow_engine import FlowEngine
    from opsflow.models import FlowExecution
    execution = FlowExecution.objects.get(id=_execution_id)
    execution.context['_pause_reason'] = 'approval'
    execution.context['_approvers'] = approvers
    execution.save(update_fields=['context'])
    FlowEngine(execution).pause()
    return True
```

**重构后** — 不再有特殊 Approval 分支，所有审批走 ITSM：

```python
# after: 该分支已完全移除，atom_type='approval' 不会再出现
# 审批改为 ITSM 工单 + 自动任务节点(OpsflowAutoTaskNode) 的模式
```

**重构前** — ITSM ticket_views.py 审批回调：

```python
# backend/itsm/views/ticket_views.py (删除)
if result == 'true':
    trigger_result = OpsflowTriggerService.on_ticket_approved(instance)
    if trigger_result.get('triggered'):
        logger.info(...)
```

**重构后** — 自动任务节点回调模式：

```python
# backend/itsm/services/auto_task_service.py (现有)
class ItsmAutoTaskService:
    """ITSM 自动任务(TASK)节点绑定 OpsFlow 模板
    当 ITSM 工单到达自动任务节点时，触发 OpsFlow 执行，
    OpsFlow 完成后通过回调通知 ITSM 继续流转。
    """
    @staticmethod
    def on_opsflow_finished(execution, ...):
        """OpsFlow 执行完成后的回调"""
```

### 设计决策

1. **为什么不保留两个审批通道？** ITSM 审批已覆盖全部场景（委托、SLA、多级审批），OpsFlow 内嵌审批是重复功能，维护两份代码成本高。
2. **为什么 SubmitWizardDialog 也从 ServiceNow 切到 ITSM？** 项目没有对接 ServiceNow，旧代码使用 mock 接口无法正常工作。ITSM 已有完整的变更工单模型，直接复用。
3. **数据迁移而非软删除？** `PageTab` 和 `IAMPermission` 通过 FK CASCADE 自动清理关联的 role-permission 绑定，硬删除干净无残留。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/plugins/approval/approval.py` | 删除 — ApprovalPlugin 完整实现 |
| `backend/opsflow/core/plugin_service_adapter.py:99-119` | 删除 — approval 特殊处理分支 |
| `backend/itsm/services/opsflow_trigger.py` | 删除 — TicketOpsflowConfig 模型 + OpsflowTriggerService |
| `backend/iam/migrations/0003_remove_opsflow_approvals_tab.py` | 新增 — 清理遗留的权限和页面标签 |
| `web/src/views/apps/opsflow-approval/index.vue` | 删除 — 审批中心完整页面 |
| `web/src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue` | 修改 — ServiceNow → ITSM 变更工单 |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue` | 修改 — 移除 `isApproval` 分支和用户加载 |
| `web/src/i18n/pages/opsflow/en.ts` + `zh-cn.ts` | 修改 — 移除约 50 个 approval 相关键 |

## 使用方式

**旧方式（已删除）：**
- 在流程设计器中放置 approval 节点 → 设置审批人 → 执行到该节点暂停 → 去审批中心处理

**新方式（推荐）：**
- 审批走 ITSM 工单流程 → 在 ITSM 流程中放置自动任务节点关联 OpsFlow 模板 → OpsFlow 完成后自动回调 ITSM 继续流转

### 关联文档

- 相关功能文档: [2026-06-29-approval-refactor-plugin.md](../features/2026-06-29-approval-refactor-plugin.md)
- 相关功能文档: [2026-07-13-itsm-autotask-opsflow-integration.md](../../itsm/features/2026-07-13-itsm-autotask-opsflow-integration.md)
