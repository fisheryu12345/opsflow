# Exclusive Gateway 条件表达式修复 + 驳回流程清理

> 最后更新: 2026-07-10
> 涉及版本: f689e639

---

## 1. 背景与现象

ITSM 工作流中 Exclusive Gateway 的条件分支无法正确求值，表现为：

1. **条件表达式格式错误** — `workflow_builder.py` 将条件包裹在 `{'evaluate': expr}` 字典中传给 `add_condition()`，而 OpsFlow 的 `BoolRule` 要求原始表达式字符串（如 `${node_1.field} == 'x'`）
2. **驳回后重新提交状态残留** — 审批驳回后 `TicketStatus` 和 `node_status` 未完全清理，导致重新提交时节点状态混乱
3. **提交时自动完成首节点冲突** — `do_in_state()` 提前完成 NORMAL 节点，与 pipeline engine callback 产生竞态
4. **ElInputNumber 空值异常** — 数字类型字段收到空字符串 `""` 时组件报错

**表现：**
- 网关分支始终走默认分支（条件求值失败）
- 驳回后重新提交工单，审批节点显示异常状态
- 数字字段在表单渲染时出现控制台警告

---

## 2. 排查思路

### 2.1 条件表达式格式排查

对比 OpsFlow（已验证）和 ITSM 的网关条件生成逻辑：

```
OpsFlow: add_condition(0, "${node_2.field} == 'x'")   ← 原始字符串
ITSM:    add_condition(0, {'evaluate': "${node_2.field} == 'x'"})  ← 错误包裹
```

查看 `bamboo_engine.builder.BuilderElement.add_condition()` 的签名确认参数期望是字符串。

### 2.2 驳回流程排查

跟踪驳回链路：
```
ItsmApprovalService.schedule() → revoke_pipeline() → set_status('draft')
                                  ↑ 但未清理 TicketStatus 和 node_status
```

### 2.3 提交流程排查

`TicketViewSet.submit()` 中 `do_in_state()` 在 pipeline engine 启动前就完成了首节点，随后 engine callback 尝试再次推进同一节点导致状态冲突。

### 2.4 数字字段排查

`ElInputNumber` 组件要求 `model-value` 为 `number | null | undefined`，但表单数据中数字字段初始值为空字符串 `""`。

---

## 3. 根因分析

### 3.1 条件表达式格式

```
┌──────────────────────────────────────────────────────────┐
│ workflow_builder.py  _build_gateway_conditions()         │
│                                                          │
│ 修复前: from_el.add_condition(i, {'evaluate': expr})     │
│         → bamboo_engine 收到 {"evaluate": "..."}          │
│         → BoolRule 解析时无法识别，条件恒为 False          │
│                                                          │
│ 修复后: from_el.add_condition(i, expr)                   │
│         → bamboo_engine 直接收到 "${n1.f} == 'x'"        │
│         → BoolRule 正确解析并求值                          │
└──────────────────────────────────────────────────────────┘
```

### 3.2 驳回状态残留

```
驳回前: TicketStatus(RUNNING), node_status={'node_1': 'RUNNING'}
驳回后(旧): pipeline revoked, ticket=draft, 但 TicketStatus/ node_status 未清理
驳回后(新): TicketStatus→WAIT, node_status={}
```

### 3.3 提交竞态

```
submit() 旧流程:
  do_in_state(first_node, form_data)  ← 提前完成
  engine.run()                         ← 启动 pipeline
  activity_callback()                  ← 又尝试推进 first_node → 冲突

submit() 新流程:
  TicketStatus→WAIT   ← 仅重置状态
  engine.run()         ← 启动 pipeline
  activity_callback()  ← 正常推进 first_node ✓
```

---

## 4. 解决方案

### 4.1 `backend/itsm/services/workflow_builder.py`

- **改动：** `from_el.add_condition(i, {'evaluate': expr})` → `from_el.add_condition(i, expr)`
- **目的：** 匹配 OpsFlow `BoolRule` 的原始字符串格式

### 4.2 `backend/itsm/pipeline_plugins/components.py`

- **改动：** 驳回时新增 `TicketStatus.objects.filter(ticket=ticket, status='RUNNING').update(status='WAIT')` 和 `ticket.node_status = {}`
- **目的：** 彻底清理驳回后的状态残留，确保重新提交时无历史状态干扰

### 4.3 `backend/itsm/views/ticket_views.py`

- **改动：** 移除 `instance.do_in_state(first_normal_id, form_data, 'system')` 及其 `form_data` 清理逻辑；在 `engine.run()` 前添加 `TicketStatus.objects.filter(ticket=instance).update(status='WAIT')`
- **目的：** 消除提交时的竞态条件，由 pipeline engine callback 统一推进首节点；重置所有 TicketStatus 为 WAIT 保留审批历史

### 4.4 `web/src/components/ItsmFormRenderer/ItsmFormField.vue`

- **改动：** 新增 `safeModelValue` computed，将空字符串 `""` 转为 `null`（仅对 INT/NUMBER/FLOAT 类型）
- **目的：** 兼容 `ElInputNumber` 的值类型要求

### 4.5 `web/src/views/apps/itsm/FlowChart.vue`

- **改动：** 边颜色统一为 `#E6A23C`
- **目的：** 移除基于 `isReject` 的条件着色，简化渲染逻辑

### 4.6 `web/src/views/apps/itsm/TicketDetail.vue`

- **改动：** SLA 网格布局添加 `justify-content: space-between` + `flex: 1`
- **目的：** 修复 SLA 卡片在宽屏下的间距不均匀问题

---

## 5. 引入的方法 / 函数 / 设计模式

| 引入内容 | 所在文件 | 说明 |
|---------|---------|------|
| `safeModelValue` computed | `web/src/components/ItsmFormRenderer/ItsmFormField.vue:70` | 将空字符串转为 null，兼容 ElInputNumber |
| `TicketStatus.objects.filter(...).update(status='WAIT')` | `backend/itsm/pipeline_plugins/components.py:163` | 驳回后批量重置状态 |
| `TicketStatus.objects.filter(ticket=instance).update(status='WAIT')` | `backend/itsm/views/ticket_views.py:93` | 提交前批量重置状态，保留审批历史 |

---

## 6. 验证

- 网关条件分支：在 ITSM 设计器中配置多条件 Exclusive Gateway → 提交工单 → 验证各分支按条件正确路由
- 驳回重新提交：审批驳回 → 修改表单 → 重新提交 → 确认 TicketStatus 和 node_status 为干净状态
- 数字字段：创建含 INT 字段的工单 → 留空提交 → 确认无控制台错误

---

## 7. 涉及文件清单

- `backend/itsm/services/workflow_builder.py` — 修复 `add_condition()` 参数格式
- `backend/itsm/pipeline_plugins/components.py` — 驳回后清理 TicketStatus 和 node_status
- `backend/itsm/views/ticket_views.py` — 提交前批量重置 TicketStatus，移除 do_in_state 提前完成
- `web/src/components/ItsmFormRenderer/ItsmFormField.vue` — 数字字段空值兼容
- `web/src/views/apps/itsm/FlowChart.vue` — 边颜色统一
- `web/src/views/apps/itsm/TicketDetail.vue` — SLA 网格布局修复
