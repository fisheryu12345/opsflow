# ITSM 节点稳定标识（node_key）与设计器增强

> 提交: 847774f9 | 日期: 2026-07-05
> 涉及 App: itsm
> 类型: 功能新增

---

## 背景

ITSM 设计器使用 X6 图形库，每个节点在画布上有自己的 cell ID。但此前 WorkflowVersion 快照使用 State 的数据库 ID（`s.id`）作为 states dict 的 key，导致以下问题：

1. **设计/运行态 key 不一致** — 前端用 cell ID/node_key 引用节点，后端用 state_id，Pipeline activity ID 和 node_status 的 key 不匹配
2. **START/END 内置节点缺失** — 草稿流程部署时，START/END 可能尚未持久化到 DB，导致快照中缺失
3. **工单详情无内联填单** — 审批节点可以操作，但 NORMAL 填单节点在工单详情中没有内联表单

本次增加 `node_key` 贯穿设计器 → Workflow → WorkflowVersion → Ticket → Pipeline 整条链路，做 stable identity。

## 实现方案

### 核心架构 / 设计

在 State 和 Transition 模型上增加 node_key / from_node_key / to_node_key 字段，用作：

- **设计时**: 前端 X6 节点生成唯一 `node_N` 标识，贯穿拖拽 → 保存 → 加载
- **快照时**: Workflow.create_version() 用 node_key 作为 states dict 的 key（替代 DB id）
- **运行时**: Ticket.get_state()/do_before_enter_state() 用 node_key 查找状态、作为 Pipeline activity ID

### 关键代码

#### State 模型新增 node_key

```python
# backend/itsm/models/state.py
class State(CoreModel):
    node_key = models.CharField(max_length=32, null=True, blank=True, db_index=True,
                                verbose_name="前端节点标识")
    is_builtin = models.BooleanField(default=False, verbose_name="内置节点")
    
    class Meta:
        unique_together = [('workflow', 'node_key')]
```

相同 workflow 内 node_key 唯一，保证设计器保存时按 node_key 做 upsert 而非按 DB id。

#### Transition 模型新增 node_key

```python
# backend/itsm/models/transition.py
class Transition(CoreModel):
    from_node_key = models.CharField(max_length=32, null=True, blank=True, db_index=True,
                                     verbose_name="源节点标识")
    to_node_key = models.CharField(max_length=32, null=True, blank=True, db_index=True,
                                   verbose_name="目标节点标识")
```

#### Workflow.create_version() 使用 node_key 做快照 key

```python
# backend/itsm/models/workflow.py
def create_version(self, operator, message=''):
    states_data = {}
    for s in self.states.all():
        key = s.node_key or s.id  # 优先用 node_key
        states_data[key] = {
            'id': s.id, 'node_key': s.node_key or '', ...
        }
    # Safety net: 确保 START/END 存在
    if '__start__' not in states_data:
        states_data['__start__'] = {'id': -1, 'node_key': '__start__', ...}
    if '__end__' not in states_data:
        states_data['__end__'] = {'id': -2, 'node_key': '__end__', ...}
```

#### Ticket.get_state() 支持 node_key 查找

```python
# backend/itsm/models/ticket.py
def get_state(self, state_id):
    states = self.workflow_version.states or {}
    key = str(state_id)
    if key in states:
        return states[key]
    # Fallback: 按 state['id'] 或 state['node_key'] 查找
    for s in states.values():
        if str(s.get('id')) == key or str(s.get('node_key')) == key:
            return s
    return {}
```

#### Pipeline activity ID 用 node_key

```python
# backend/itsm/views/ticket_views.py
def _get_activity_id(ticket, state_id):
    states = (ticket.workflow_version and ticket.workflow_version.states) or {}
    key = str(state_id)
    if key in states:
        return str(states[key].get('node_key') or key)
    for s in states.values():
        if str(s.get('id')) == key:
            return str(s.get('node_key') or key)
    return str(state_id)
```

#### 前端设计器 node_key 自动生成

```typescript
// web/src/views/apps/itsm/designer/useDesigner.ts
// 节点拖入时自动生成 node_N 格式标识
if (!data.node_key) {
  let maxN = 0
  for (const cell of g.getNodes()) {
    const nk = cell.getData()?.node_key || ''
    const m = nk.match(/^node_(\d+)$/)
    if (m) maxN = Math.max(maxN, parseInt(m[1], 10))
  }
  data.node_key = `node_${maxN + 1}`
}
```

#### WorkflowViewSet StateSync 按 node_key 差异同步

```python
# backend/itsm/views/workflow_views.py
@action(methods=['POST'], detail=False)
def sync(self, request):
    existing = {s.node_key: s for s in State.objects.filter(workflow_id=workflow_id) if s.node_key}
    incoming_keys = set()
    for s in states:
        nk = s.get('node_key')
        if nk and nk in existing:
            State.objects.filter(id=existing[nk].id).update(**clean)
            incoming_keys.add(nk)
        else:
            new_state = State.objects.create(**clean)
            incoming_keys.add(new_state.node_key or str(new_state.id))
    to_delete = set(existing.keys()) - incoming_keys
    State.objects.filter(node_key__in=to_delete).delete()
```

### 其他增强

**SLA 暂停/恢复增强（sla_engine.py）：**
- `SlaEngine.start_ticket_sla()` 改用 `get_or_create` 而非 `update_or_create`，防止覆盖正在运行的 SLA 计时器
- `pause_ticket_sla()` 记录 `paused_at` 时间戳
- `resume_ticket_sla()` 用暂停时长补偿 deadline，而非重新计算
- 新增 SlaTask.paused_at 字段

**前端工单详情内联填单（index.vue）：**
- NORMAL 节点在 RUNNING 状态时，自动渲染其字段定义（TEXT/SELECT/FILE 等）
- 审批/会签节点仍保留通过/驳回按钮
- 从 WorkflowVersion states 快照中合并字段定义到 node_status

### 数据流

```
设计器拖入节点
  → X6 生成 cell ID + useDesigner 分配 node_key (node_1, node_2...)
  → StateSync POST {node_key, name, type...}
  → 后端按 node_key upsert State 记录
  → Workflow.create_version() 以 node_key 为 key 存储快照
  → Pipeline 执行时 _get_activity_id() 用 node_key 映射 activity
  → Ticket.do_before_enter_state() 以 node_key 记录 node_status
  → 工单详情用 node_status key 关联 WorkflowVersion 字段定义
```

### 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| node_key 生成策略 | 前端 `node_N` 递增 | 简单、可读、与 X6 cell ID 解耦 |
| 快照 key | node_key 优先，fallback id | 向后兼容已有流程版本 |
| START/END 内置节点 | 快照中自动补全 | 防止草稿部署时缺失 |
| StateSync 标识 | node_key 作为稳定标识 | 支持设计器重做/撤销而不丢失关联 |
| SLA start 策略 | get_or_create 不覆盖 | 防止审批节点重复触发 SLA 重置 |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/itsm/models/state.py:37-38` | node_key + is_builtin 字段 |
| `backend/itsm/models/transition.py:22-25` | from_node_key + to_node_key 字段 |
| `backend/itsm/models/workflow.py:58-76` | create_version 用 node_key 做 key |
| `backend/itsm/models/ticket.py:95-104` | get_state 支持 node_key 查找 |
| `backend/itsm/views/workflow_views.py:248-275` | StateSync 按 node_key 差异同步 |
| `backend/itsm/views/ticket_views.py:253-262` | _get_activity_id 用 node_key |
| `backend/itsm/services/workflow_builder.py:57-58` | builder 用 node_key 映射 transition |
| `backend/itsm/services/sla_engine.py:51-80` | SLA pause/resume 增强 |
| `web/src/views/apps/itsm/designer/useDesigner.ts:120-145` | 前端 node_key 自动生成 + 初始化 |
| `web/src/views/apps/itsm/index.vue:448-472` | 工单详情内联填单表单 |

## 使用方式

- **设计器**: 节点拖入自动分配 node_key，保存/加载全自动，无需手动配置
- **工单详情**: NORMAL 节点在 RUNNING 状态时自动显示表单字段，填写后点击"提交"
- **SLA**: 挂起/恢复工单时 SLA 计时器自动暂停/补偿，无需人工干预
- **开发者**: 无额外操作，DB migration 自动填充

---

## 2026-07-05 Update

> 提交: 88b61c0f

### 变更内容

- ticket.py: SignTask 通过 TicketStatus pk 查询修复（state_id 改为 status 外键）
- sla_engine.py: 支持 stopped 状态 SLA 重置，审批节点复用同一 SLA 时正确重置
- workflow_builder.py: element_map 同时注册 DB id（支持 transition 按 from_state_id 回退查找）
- workflow_views.py: rollback 时保留 node_key；StateSync 保护无 node_key 旧状态不被误删；transition 同步保留 condition_type/direction
- useDesigner.ts: 清理 console.log 调试输出；修复连线 _from_state/_to_state 引用为 cell ID

### 原因

node_key 稳定标识首次实现后，rolling deploy 和版本回滚场景下发现 state_id → node_key 映射不够完整，导致部分旧流程兼容性问题
