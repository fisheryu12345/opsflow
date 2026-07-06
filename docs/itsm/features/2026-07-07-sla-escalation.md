# SLA 端到端计时与升级层级体系

> 提交: bafc693b | 日期: 2026-07-07
> 涉及 App: itsm, iam
> 类型: 功能新增

---

## 背景

当前 ITSM 的 SLA 机制与 pipeline 流程存在多处断裂：

1. **SLA 启动/停止时序混乱** — `do_before_enter_state`（仅 APPROVAL/SIGN）和 `post_set_state` 信号（所有节点）双重触发；`do_before_exit_state` 只停 APPROVAL/SIGN 导致计时器行为不一致
2. **SLA 检查没有定时运行** — `tasks.py` 中 `sla_check` Celery task 从未加入 Celery Beat，只能人工执行
3. **SLA 超时无动作** — 超时后只写 `ticket.meta.sla_history`，不发送通知、不触发升级
4. **SLA 数据前端不可见** — 工单列表、详情、仪表板都不显示 SLA 倒计时/状态
5. **仪表板超时计算用 7 天硬编码**而非实际的 SLA deadline

## 实现方案

### 核心架构

SLA 从**工单提交（pipeline 启动）**开始到**工单完成（pipeline 结束）**全程计时，暂停/恢复补偿机制保留。

```
旧架构:
  do_before_enter_state → start_ticket_sla (仅 APPROVAL/SIGN)
  post_set_state 信号   → start_ticket_sla (所有节点, 无条件)
  do_before_exit_state  → stop_ticket_sla (仅 APPROVAL/SIGN)

新架构:
  ITSMEngine.run() 成功后 → start_ticket_sla (只此一次)
  pipeline EndEvent      → do_before_end_pipeline → stop_ticket_sla
  ticket_post_save 信号  → pause/resume/stop (按状态)
```

### 关键代码

#### 1. 端到端 SLA 启动

`backend/itsm/services/itsm_engine.py` — `run()` 成功后调用 `SlaEngine.start_ticket_sla()`

```python
def run(self, workflow_version):
    ...
    result = pipeline_api.run_pipeline(runtime, tree)
    if not result.result:
        raise RuntimeError(...)
    # 端到端 SLA 启动（只此一次）
    try:
        from itsm.services.sla_engine import SlaEngine
        SlaEngine.start_ticket_sla(self.ticket)
    except Exception as e:
        logger.warning('[ITSMEngine] SLA start failed: %s', e)
    return pipeline_id, tree
```

#### 2. 移除节点级 SLA 控制

`backend/itsm/models/ticket.py` — `do_before_enter_state()` 移除了 `SlaEngine.start_ticket_sla()` 调用，`do_before_exit_state()` 变为预留空钩子：

```python
def do_before_exit_state(self, state_id, operator=''):
    """Exit state pre-processing (currently a reserved hook; SLA stop is handled uniformly at pipeline end)"""
    pass
```

`backend/itsm/signals.py` — `itsm_post_set_state_handler` 移除了对 `states.RUNNING` 的 SLA 启动：

```python
# SLA start unified in ITSMEngine.run() — no longer triggered per-node
if to_state == states.RUNNING:
    pass
```

#### 3. APScheduler 定时 SLA 检查

`backend/itsm/apps.py` — `ready()` 中启动独立 `BackgroundScheduler`（追随 monitor 模式），不再依赖 Celery Beat：

```python
if os.environ.get('RUN_MAIN') or os.environ.get('DJANGO_AUTORELOAD'):
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    tz = getattr(settings, 'TIME_ZONE', 'Asia/Shanghai')
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(sla_check_job, trigger=IntervalTrigger(seconds=60), ...)
    scheduler.start()
    self._sla_scheduler = scheduler  # prevent GC
```

`backend/itsm/sla_check_job.py` — 新文件，普通函数不再依赖 Celery：

```python
def sla_check_job():
    result = SlaEngine.check_all_active_sla()
    ...
```

#### 4. 超时通知

`backend/itsm/services/sla_engine.py` — `_execute_escalation()` 新增 `notify_sla_violation` 调用：

```python
@staticmethod
def _execute_escalation(ticket, esc_type='timeout'):
    ...
    # 发送超时通知
    try:
        from itsm.services.notifications import NotificationService
        NotificationService.notify_sla_violation(ticket)
    except Exception as e:
        logger.error(f'SLA notification failed: {e}')
```

#### 5. SLA 数据暴露到前端

`backend/itsm/serializers/ticket_serializers.py` — `TicketSerializer` 新增 `sla_info` 字段，通过 `prefetch_related` 消除 N+1：

```python
class TicketSerializer(CustomModelSerializer):
    sla_info = serializers.SerializerMethodField()

    @staticmethod
    def get_sla_info(obj):
        task = next(iter(obj.sla_tasks.all()), None)
        if not task:
            return None
        ...
        return {
            'deadline': ...,
            'reply_deadline': ...,
            'remaining_seconds': remaining,
            'task_status': task.task_status,
            'sla_status': task.sla_status,
            'policy_name': task.sla_policy.name if task.sla_policy else None,
        }
```

`backend/itsm/views/ticket_views.py` — `TicketViewSet.queryset` 添加 `prefetch_related`：

```python
queryset = Ticket.objects.prefetch_related(
    models.Prefetch('sla_tasks', queryset=SlaTask.objects.select_related('sla_policy'))
)
```

前端 `index.vue` — 工单表格新增 SLA 列，显示剩余时间和状态标签（绿/黄/红）：

```vue
<el-table-column label="SLA" width="100">
  <template #default="{ row }">
    <span v-if="row.sla_info" :class="'sla-badge sla-' + row.sla_info.sla_status">
      {{ row.sla_info.remaining_seconds != null ? formatSla(row.sla_info.remaining_seconds) : '-' }}
    </span>
  </template>
</el-table-column>
```

前端 `TicketDetail.vue` — 新增 SLA 信息卡片：

```vue
<div class="td-sla-card" :class="'sla-' + ticket.sla_info.sla_status" v-if="ticket?.sla_info">
  <div class="td-sla-grid">
    <div class="td-sla-item"><span class="td-sla-label">状态</span> <span :class="'sla-badge sla-' + ...">...</span></div>
    <div class="td-sla-item"><span class="td-sla-label">剩余时间</span> <span>...</span></div>
    <div class="td-sla-item"><span class="td-sla-label">响应截止</span> <span>...</span></div>
    <div class="td-sla-item"><span class="td-sla-label">解决截止</span> <span>...</span></div>
  </div>
</div>
```

#### 6. 仪表板 deadline 改造

`backend/itsm/views/dashboard.py` — 超时统计从 "7 天硬编码" 改为 `SlaTask.deadline`：

```python
# Old: Ticket.objects.filter(create_datetime__lt=week_ago)
# New:
overdue_count = SlaTask.objects.filter(
    deadline__lt=now, task_status='running',
    ticket__current_status__in=ACTIVE_STATUSES,
).count()
```

前端 `Dashboard.vue` — 超时列表显示 `overdue_seconds` 格式化后的时长（如 "2天3小时"）：

```typescript
function formatOverdue(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return '-'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  if (d > 0) return `${d}天${h}小时`
  if (h > 0) return `${h}小时`
  return `${Math.floor(seconds / 60)}分钟`
}
```

#### 7. 升级层级体系

`backend/itsm/models/escalation.py` — 新建 `EscalationLevel` 模型：

```python
class EscalationLevel(CoreModel):
    name = CharField(max_length=128, verbose_name="级别名称")
    level = IntegerField(default=1, verbose_name="级别序号")
    timeout_minutes = IntegerField(default=60, verbose_name="超时阈值(分钟)")
    action = CharField(choices=('notify_only','transfer_leader','transfer_next','notify_users'), ...)
    notify_users = TextField(blank=True, default='', ...)
    is_active = BooleanField(default=True)
```

`backend/itsm/views/escalation_views.py` — `EscalationLevelViewSet(ModelViewSet)`，非项目隔离的全局配置。

前端 `index.vue` — 完整的升级 Tab（表格 + 编辑对话框）：

- 表格列：级别、名称、超时阈值、升级动作、启用开关、操作按钮
- 编辑对话框：级序号、名称、超时阈值、动作选择、用户多选搜索、启用开关
- `escalationApi` 通过 `createCrudApi('escalation-levels')` 自动生成

#### 8. 清理

- `models/sla.py` — 移除 `PriorityMatrix` 类（从未使用）
- `models/sla.py` — 移除 `SlaTask.cost_seconds` 字段（从未更新）
- Migration `0011_delete_prioritymatrix_remove_slatask_cost_seconds` + `0012_remove_escalationlevel_skill_group`

### 数据流

```
工单提交 → ITSMEngine.run() → start_ticket_sla()
                              → SlaTask(deadline=now+response_min, task_status=running)
                              → SLA 定时检查每 60s 执行
                                  → deadline < now → VIOLATED → _execute_escalation()
                                                              → notify_sla_violation()
                              → 工单详情/列表读取 sla_info → 前端显示倒计时

工单暂停 → set_status('suspended') → ticket_post_save → pause_ticket_sla()
工单恢复 → set_status('running')   → ticket_post_save → resume_ticket_sla() 补偿暂停时长
工单结束 → pipeline EndEvent       → do_before_end_pipeline → stop_ticket_sla()
```

### 设计决策

| 决策 | 选项 | 选择理由 |
|------|------|----------|
| SLA 启动时机 | 节点级 vs 端到端 | 端到端 — SLA 承诺的是服务级别，不是节点级别。用户提 P1 事件工单承诺 60 分钟解决，而不是每个审批节点分别计时 |
| 定时调度 | Celery Beat vs APScheduler | APScheduler — 项目已使用 `django_apscheduler`（opsflow scheduler_service），避免 Celery Beat 额外依赖 |
| 升级模型 | 全局配置 vs 项目隔离 | 全局 — 升级级别是平台级策略，不按项目区分 |
| 通知用户控件 | 文本输入 vs 多选搜索 | 多选搜索 — 复用已有的 `/api/iam/users/search/` 接口，避免手动输入用户名的拼写错误 |
| N+1 优化 | `prefetch_related` + `next(iter(...))` | 避免列表页每行额外查询，通过反向关联 `sla_tasks` 预取 |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/services/itsm_engine.py` | SLA 启动点 — `run()` 成功后调用 `start_ticket_sla()` |
| `backend/itsm/models/ticket.py` | 移除节点级 SLA 控制，`do_before_exit_state` 变为空钩子 |
| `backend/itsm/signals.py` | 移除 `post_set_state` 对 `states.RUNNING` 的 SLA 启动 |
| `backend/itsm/apps.py` | APScheduler `BackgroundScheduler` 注册与启动 |
| `backend/itsm/sla_check_job.py` | 新建 — SLA 定时检查普通函数 |
| `backend/itsm/services/sla_engine.py` | `_execute_escalation` 新增 `notify_sla_violation` |
| `backend/itsm/serializers/ticket_serializers.py` | `sla_info` SerializerMethodField |
| `backend/itsm/views/ticket_views.py` | `prefetch_related('sla_tasks')` 消除 N+1 |
| `backend/itsm/views/dashboard.py` | 超时统计改用 `SlaTask.deadline` |
| `backend/itsm/models/escalation.py` | 新建 — `EscalationLevel` 模型 |
| `backend/itsm/views/escalation_views.py` | 新建 — `EscalationLevelViewSet` |
| `backend/itsm/urls.py` | 注册 `escalation-levels` 路由 |
| `backend/itsm/models/sla.py` | 清理 — 删除 `PriorityMatrix`、`cost_seconds` |
| `web/src/api/itsm/index.ts` | 新增 `escalationApi` |
| `web/src/views/apps/itsm/index.vue` | SLA 表格列 + 升级 Tab（CRUD 对话框 + 用户多选） |
| `web/src/views/apps/itsm/TicketDetail.vue` | SLA 信息卡片 |
| `web/src/views/apps/itsm/Dashboard.vue` | 超时列表改用 `overdue_seconds` |
| `backend/iam/management/commands/seed_iam_page_configs.py` | 升级 Tab 权限配置 |

## 使用方式

### 管理员配置
1. 进入 ITSM → 升级 Tab → 新建升级级别
2. 配置级别序号、名称、超时阈值（分钟）、动作（仅通知/转组长/升级到下一级/通知用户）
3. 通知用户通过搜索多选选择
4. 保存后生效

### 用户视角
- 工单列表新增 SLA 列，显示剩余时间（绿色正常/黄色即将超时/红色已超时）
- 工单详情页显示 SLA 信息卡片（状态、策略名、倒计时、截止时间）
- 仪表板超时工单列表显示基于实际 SLA deadline 的超时时长
- SLA 超时时自动发送站内通知给提单人

### 种子数据
```bash
python manage.py seed_itsm --force  # 创建 3 级默认升级
python manage.py seed_iam_page_configs  # 注册升级 Tab
```

### 关联文档

- 相关功能文档: [服务市场统一建单入口](features/2026-06-XX-service-market-unified-entry.md)
