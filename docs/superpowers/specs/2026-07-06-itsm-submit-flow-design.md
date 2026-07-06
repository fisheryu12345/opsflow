# ITSM 提交流程重构设计

> 设计文档 — 解决服务目录提交后重复填表、分派机制双轨、流转可视化缺失的问题

## 1. 背景

### 1.1 当前问题

用户在服务市场（服务目录）提交申请时，当前流程存在三个问题：

**问题 1 — 重复填表：** 用户在 `ServiceDetail.vue` 填写表单（标题 + 优先级 + form_data）提交后，后端将 `form_data` 仅存入 `ticket.meta`，pipeline 启动后第一个 NORMAL（fill_form）节点并不知道这些数据，导致用户需要在工单详情里再次填写同样的字段。

**问题 2 — 分派双轨制：** 系统存在两套独立的分派机制——`AssignEngine.auto_assign()` 按 `AssignRule` 规则匹配设置 `ticket.meta.assignee`，而 pipeline 节点的 `processors` 配置也指定了处理人。两套机制互不知晓对方，导致工单列表显示的"处理人"可能与实际 pipeline 等待的人不一致。

**问题 3 — 流转可视化不足：** 工单详情是一个 el-dialog 弹窗，仅展示简单的节点状态列表，用户无法直观看到完整的流程步骤、已完成的节点历史、以及每一步的处理人。

### 1.2 设计目标

- 服务目录提交后自动完成第一个 NORMAL 节点，用户无需二次填表
- 统一分派机制：由节点 processors 驱动，消除双轨制
- 提供独立工单详情页，包含流程步骤条和时间线
- 修改量最小化，不改动核心引擎

## 2. 设计决策

### 2.1 提交即填单（方案 A）

**决策：** pipeline 启动后立即自动回调第一个 NORMAL 节点，将 form_data 作为 callback_data 注入。

**理由：**
- 改动最小——只需在 `_submit_flow()` 尾部加一行调用
- 重用已有的 `ItsmFillFormService.schedule()` 逻辑
- NORMAL 节点状态正常记录为 FINISHED，下游条件可引用字段值
- 不修改 pipeline 组件或 builder

**不选方案 B（ServiceActivity 注入初始数据）的原因：** 需要修改组件 execute() 逻辑，耦合性更高，且需额外处理组件生命周期。

### 2.2 分派机制统一

**决策：** 移除 `AssignRule` 自动分派（`auto_assign()`），`ticket.meta.assignee` 由 pipeline 当前 RUNNING 节点的 `processors` 解析结果自动填充。

**理由：**
- 每个流程节点在设计器中已预制 `processors_type` + `processors`
- `role_resolver.py` 已有完整的解析逻辑（PERSON、STARTER、STARTER_LEADER、ROLE...）
- `AssignRule` 的匹配功能（`to_group`、`to_onduty`、`least_busy`）均可被节点 processors 覆盖
- 唯一缺失的 `least_busy` 模式可以通过新增 `processors_type = 'LEAST_BUSY'` 实现，而非独立规则引擎

**保留的：** `AssignEngine.manual_assign()` — 用于手动转派/干预。

### 2.3 流转可视化

**决策：** 新建独立工单详情页 `TicketDetail.vue`，替换当前的 el-dialog 弹窗。

包含：
- 顶部 el-steps 步骤条——展示完整流程步骤，高亮当前节点
- 已完成节点时间线——显示处理人、完成时间、审批意见
- 当前节点操作区——审批（通过/拒绝）或填单表单
- 路由 `/apps/itsm/ticket/:id`

## 3. 详细设计

### 3.1 后端改动

#### 3.1.1 `service_item.py` — 自动回调第一个 NORMAL 节点

```python
# _submit_flow() 尾部追加
def _auto_complete_first_node(ticket, form_data):
    """查找第一个 NORMAL 节点，用 form_data 自动回调"""
    if not form_data or not ticket.workflow_version:
        return
    states = ticket.workflow_version.states or {}
    first = next(
        (s for s in states.values() if s.get('type') == 'NORMAL'), None
    )
    if not first:
        return
    node_key = str(first.get('node_key') or first.get('id'))
    id_map = (ticket.meta or {}).get('_pipeline_id_map', {})
    activity_id = id_map.get(node_key) or id_map.get(str(first.get('id')))
    if not activity_id:
        logger.warning("...")
        return
    ITSMEngine.activity_callback(activity_id, {
        'ticket_id': ticket.id,
        'state_id': first['id'],
        'fields': form_data,
        'operator': 'system',
    })
```

调用位置：`ITSMEngine(ticket).run(version)` 成功返回之后。

#### 3.1.2 `ticket.py` — `do_before_enter_state()` 写入 assignee

```python
def do_before_enter_state(self, state_id, operator=''):
    # ... 现有逻辑（创建 TicketStatus，设置 node_status）...
    
    # 🆕 将节点处理人同步到 ticket.meta.assignee（用于工单列表显示）
    resolved = self._resolve_processors_for_display(state_data)
    if resolved:
        meta = dict(self.meta or {})
        meta['assignee'] = resolved
        self.meta = meta
        self.save(update_fields=['meta'])
```

#### 3.1.3 `ticket_views.py` — 移除 `submit()` 中的 auto_assign 调用

```python
# 移除以下代码
# from itsm.services.assign_engine import AssignEngine
# engine = AssignEngine(instance, project_id=instance.project_id)
# engine.auto_assign()
```

### 3.2 前端改动

#### 3.2.1 `ServiceDetail.vue`

```typescript
// onSubmit() 成功分支
const ticketId = respData?.ticket_id
if (ticketId) {
  emit('submitted', ticketId)  // 🆕 传 ticketId
} else {
  ElMessage.success('提交成功')
  emit('back')
}
```

#### 3.2.2 `ServiceMarket.vue`

```typescript
// onSubmitted(ticketId) — 不再关闭 overlay，而是向上穿透
function onSubmitted(ticketId: number) {
  showDetail.value = false
  emit('goTicket', ticketId)  // 🆕 向上穿透
}
```

在 template 中绑定：`@submitted="onSubmitted"`

#### 3.2.3 `index.vue`

```typescript
// 监听 ServiceMarket 的 goTicket 事件
function onGoTicket(ticketId: number) {
  activeTab.value = 'tickets'
  ticketFilter.value = 'running'
  loadTickets()
  // 跳转到独立详情页
  router.push('/apps/itsm/ticket/' + ticketId)
}
```

#### 3.2.4 `TicketDetail.vue`（新文件）

新建独立页面，包含：

**布局：**
```
┌──────────────────────────────────────────────┐
│  ← 返回工单列表  ITSM20260706-xxx            │
│  标题: xxx  状态: 处理中  优先级: P3          │
├──────────────────────────────────────────────┤
│  [填单申请] ──→ [主管审批] ──→ [结束]         │
│  ● 已完成     ▲ 当前进行中  ○ 待处理          │
├──────────────────────────────────────────────┤
│  主管审批                                     │
│  ┌──────────────────────────────────────────┐ │
│  │ 处理人: 张三  接收时间: 2026-07-06 14:30 │ │
│  │                                          │ │
│  │ 审批意见: [________]  [通过] [拒绝]      │ │
│  └──────────────────────────────────────────┘ │
├──────────────────────────────────────────────┤
│  已完成节点                                    │
│  ● 填单申请 — 李四 2026-07-06 14:00 ✅       │
│  ● 自动审批 — 系统 2026-07-06 14:01 ✅       │
└──────────────────────────────────────────────┘
```

**数据来源：**
- `GET /api/itsm/tickets/{id}/` — 工单基本信息
- `GET /api/itsm/tickets/{id}/status/` — 节点状态列表（`node_status`）
- `ticket.workflow_version.states` — 流程定义（用于 el-steps）
- `ticket.meta._pipeline_id_map` — 匹配当前活动节点

### 3.3 路由改动

```typescript
// route.ts — ITSM 路由配置中增加
{
  path: 'ticket/:id',
  name: 'ItsmTicketDetail',
  component: () => import('/@/views/apps/itsm/TicketDetail.vue'),
  meta: { title: '工单详情' },
}
```

## 4. 不改动的文件

| 文件 | 原因 |
|------|------|
| `itsm_engine.py` | 复用已有的 `activity_callback()` 和 `run()` |
| `workflow_builder.py` | pipeline 构建逻辑不变 |
| `role_resolver.py` | 已有 processors 解析逻辑，无需改动 |
| `assign_engine.py` | 保留 `manual_assign()` 用于手动转派，仅移除 `auto_assign()` |
| `pipeline_plugins/components.py` | 组件逻辑不变 |
| `ServiceAdmin.vue` | 管理界面不变 |

## 5. 数据流（修改后）

```
服务市场提交 (ServiceDetail.vue)
  → POST /api/itsm/service-items/{id}/submit/
    → _submit_flow()
      → workflow.create_version()           # 快照
      → 合并 form_fields 到第一个 NORMAL 节点
      → Ticket.create(meta={form_data, ...})
      → ITSMEngine(ticket).run(version)     # 构建 + 启动 pipeline
      → 🆕 _auto_complete_first_node()      # 自动回调第一个 NORMAL
        → activity_callback(activity_id, {fields: form_data, operator: 'system'})
        → ItsmFillFormService.schedule()    # 标记 FINISHED
        → do_before_exit_state()            # 自动前进到下一节点
  → 返回 {ticket_id, sn}
  → 前端跳转到 /apps/itsm/ticket/{id}
    → TicketDetail.vue 展示流程步骤条
    → 下一节点（如 APPROVAL）RUNNING
    → do_before_enter_state() 解析 processors
    → 🆕 自动设置 ticket.meta.assignee
    → 用户在当前节点操作区完成审批/处理
```

## 6. 验证方式

1. **单元测试：** 修改 `test_itsm_engine.py`，验证 `_auto_complete_first_node` 正确调用 activity_callback
2. **手动测试：**
   - 在服务市场选择一个流程驱动服务 → 填表提交 → 验证跳转到工单详情页
   - 验证工单详情页显示 el-steps 流程步骤条
   - 验证第一个 NORMAL 节点已标记为 FINISHED（无需再次填表）
   - 验证工单列表显示的处理人与当前节点 processors 一致
3. **边界情况：** form_data 为空时不触发自动回调；无 NORMAL 节点时不触发自动回调
