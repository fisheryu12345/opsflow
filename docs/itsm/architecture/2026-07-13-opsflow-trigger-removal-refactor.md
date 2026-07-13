# ITSM-OpsFlow 旧版触发服务移除

> 提交: 88c59d27 | 日期: 2026-07-13
> 涉及 App: itsm
> 类型: 重构

---

## 动机

ITSM 审批通过后自动触发 OpsFlow 执行的旧实现（`opsflow_trigger.py`）已被新的 **自动任务节点模式**（`ItsmAutoTaskService`）替代。旧实现在 ITSM 工单的 ticket_views.py 中硬编码回调，属于侵入式耦合，且不灵活：

- 旧 trigger 只在 **审批通过** 时触发
- 新 auto-task 节点可在 **流程任意位置** 触发 OpsFlow 模板
- 新方案支持变量映射、输出回写、回调通知

因此删除全套旧代码，包括 TicketOpsflowConfig 模型、OpsflowTriggerService 服务、TriggerAction 中的 OPSFLOW 类型。

## 变更要点

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `backend/itsm/services/opsflow_trigger.py` | TicketOpsflowConfig 模型 + OpsflowTriggerService 完整实现 (~222 行) | 删除 |
| `backend/itsm/models/__init__.py` | 从 `opsflow_trigger` import `TicketOpsflowConfig` | 移除 import |
| `backend/itsm/models/trigger.py` | TriggerAction.ACTION_TYPE_CHOICES 含 OPSFLOW | 移除 |
| `backend/itsm/services/trigger_service.py` | OpsflowRunner 类 + ActionRunner 中 OPSFLOW 分支 | 删除 |
| `backend/itsm/views/ticket_views.py` | 审批通过后调用 OpsflowTriggerService.on_ticket_approved() | 移除 |
| `backend/itsm/index.md` | 列出 `opsflow_trigger.py` 入口 | 移除 |
| `web/src/views/apps/itsm/designer/components/TriggerConfigSection.vue` | OPSFLOW action 类型的 UI 标签 + 配置面板 | 移除 |

### 代码对比

**重构前** — ticket_views.py 审批回调硬编码：

```python
# backend/itsm/views/ticket_views.py（删除）
if result == 'true':
    trigger_result = OpsflowTriggerService.on_ticket_approved(instance)
    if trigger_result.get('triggered'):
        logger.info('Ticket %s approved, triggered OpsFlow execution: %s',
                    instance.sn, trigger_result.get('execution_id'))
```

**重构后** — 通过自动任务节点解耦：

```python
# backend/itsm/services/auto_task_service.py（现有）
class ItsmAutoTaskService:
    @staticmethod
    def execute_opsflow_task(ticket, node, template_id, variable_mapping):
        """ITSM 自动任务节点触发 OpsFlow 模板执行"""
        execution = FlowExecution.objects.create(
            template_id=template_id,
            created_by=ticket.creator,
            context={"trigger": "itsm_auto_task", "ticket_id": ticket.id, ...},
        )
        engine = FlowEngine(execution)
        engine.start(sync=False)  # 异步执行
        return execution
```

**重构前** — TriggerAction 支持 OPSFLOW 类型：

```python
# backend/itsm/models/trigger.py（修改）
ACTION_TYPE_CHOICES = (
    ('NOTIFY', '发送通知'),
    ('WEBHOOK', 'HTTP 回调'),
    ('OPSFLOW', '触发运维流程'),  # 删除
    ('MODIFY_FIELD', '修改工单字段'),
)
```

**重构后** — 只保留三种标准操作：

```python
ACTION_TYPE_CHOICES = (
    ('NOTIFY', '发送通知'),
    ('WEBHOOK', 'HTTP 回调'),
    ('MODIFY_FIELD', '修改工单字段'),
)
```

### 设计决策

1. **为什么删除而非废弃？** 没有外部调用方依赖旧 trigger，且 ItsmAutoTaskService 已于 2026-07-13 上线，旧代码已不生效。
2. **为什么不保留 old/new 兼容层？** ITSM Trigger 编辑器中的 OPSFLOW 选项已在 2026-07-13 的 itsm-autotask-opsflow-integration 中用自动任务节点替代，不存在灰度迁移需求。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/services/opsflow_trigger.py` | 删除 — TicketOpsflowConfig 模型 + OpsflowTriggerService (222 行) |
| `backend/itsm/services/trigger_service.py:295-307` | 删除 — OpsflowRunner 类 |
| `backend/itsm/views/ticket_views.py:304-311` | 删除 — 审批回调 |
| `backend/itsm/models/trigger.py:68` | 修改 — 移除 OPSFLOW 选项 |
| `web/src/views/apps/itsm/designer/components/TriggerConfigSection.vue` | 修改 — 移除 OPSFLOW UI |

### 关联文档

- 相关功能文档: [2026-07-13-itsm-autotask-opsflow-integration.md](../features/2026-07-13-itsm-autotask-opsflow-integration.md)
- 相关架构文档: [2026-07-13-approval-plugin-removal-refactor.md](../../opsflow/architecture/2026-07-13-approval-plugin-removal-refactor.md)
