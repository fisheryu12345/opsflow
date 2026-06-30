# ITSM Ticket Assignment Redesign

- **Date:** 2026-06-30
- **Status:** Design approved
- **Objective:** Build a complete IT Ops ticket assignment system with skill-based routing, on-duty scheduling, multi-level escalation, and transfer auditing — using an independent APScheduler process.

## 1. Background & Problem

Current ITSM assignment has two disconnected mechanisms:

- **Manual assign** (`TicketViewSet.assign`) stores user IDs into `ticket.meta['assignees']` but is never consumed by pipeline processing at runtime.
- **Processor resolution** (`role_resolver.py`) reads `State.processors_type`/`processors` from the workflow definition at node-entry time. Manual assignment doesn't write to these fields.

Result: manual assign is a no-op for the actual workflow, and there is no auto-routing by category, no skill-group concept, no escalation, and no transfer-audit trail.

### Design decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | 分派体系覆盖哪套工单？ | **仅 pipeline-driven `Ticket`**。Legacy `Incident`/`Change` 等保持不变，不接入新体系。`Ticket` 需新增 `category` FK→ServiceCategory。 |
| 2 | 与已有 `SlaPolicy.escalate_minutes` 关系？ | **`SlaPolicy.escalate_minutes` 移除**，升级逻辑统一由 `EscalationLevel` 管理。 |
| 3 | `Ticket` 状态是否需要扩展？ | **需要**。扩充 `Ticket.STATUS_CHOICES`，增加 `assigned`（已分派）、`receiving`（待认领）等完整状态。 |

## 2. Architecture

```
┌─────────────────────────────────────────┐
│  Entry Layer — Ticket.create/submit     │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  AssignEngine (itsm/services/)          │
│  ① RuleEngine — match category+priority │
│  ② On-duty check — primary/backup       │
│  ③ Load balance — least-busy member     │
│  ④ Execute — update assignee + log      │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  Execution Layer                        │
│  Manual transfer / Auto escalation      │
│  EscalationService via APScheduler      │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  Monitoring Layer                       │
│  Team dashboard + load stats            │
│  APScheduler: timeout check per min     │
└─────────────────────────────────────────┘
```

### Scheduler Design

- **Independent process:** `python manage.py start_itsm_scheduler`
- **Stack:** `BackgroundScheduler` + `DjangoJobStore` (separate from OpsFlow's scheduler)
- **Job ID prefix:** `itsm_` to prevent collision with `opsflow_` jobs
- **Jobs:**
  | Job ID | Interval | Purpose |
  |--------|----------|---------|
  | `itsm_escalation_check` | 60s | Scan active tickets for SLA escalation triggers |
  | `itsm_sla_sync` | 300s | Sync SLA deadline updates |

## 3. Data Models

### 3.1 SkillGroup (新增)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| name | varchar(128) | required | 技能组名称, e.g. "网络组" |
| code | varchar(64) | unique, required | 编码, e.g. "net" |
| leader | FK→Users | nullable | 组长 (升级默认目标) |
| members | M2M→Users | | 组员 |
| description | text | blank | 说明 |
| is_active | boolean | default=true | 是否启用 |

### 3.2 ServiceCategory 扩展

| New Field | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| default_group | FK→SkillGroup | nullable | 默认分派技能组 |
| auto_assign | boolean | default=false | 是否启用自动分派 |

### 3.3 OnDutySchedule (新增)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| group | FK→SkillGroup | required | 技能组 |
| user | FK→Users | required | 值班人 |
| duty_date | date | required | 值班日期 |
| duty_type | varchar(16) | choice | `primary` / `backup` |

**Unique constraint:** `(group, duty_date, duty_type)` — 每组每天每种班型最多一人。

### 3.4 AssignRule (新增)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| name | varchar(128) | required | 规则名 |
| priority | int | default=100 | 匹配优先级 (数字小优先) |
| match_category | FK→ServiceCategory | nullable | 匹配服务分类 |
| match_priority | varchar(8) | nullable | 匹配优先级 P1/P2/P3/P4 |
| match_itsm_type | varchar(32) | nullable | 匹配工单类型 incident/change |
| target_group | FK→SkillGroup | required | 目标技能组 |
| assign_mode | varchar(32) | choice | `to_group` / `to_onduty` / `least_busy` |
| is_active | boolean | default=true | 是否启用 |

**Matching logic:** All non-null match fields must equal the ticket's corresponding values. Rules evaluated in ascending `priority` order; first match wins.

### 3.5 EscalationLevel (新增)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| name | varchar(128) | required | 级别名, e.g. "L1" |
| level | int | required | 升级顺序 (1→2→3) |
| group | FK→SkillGroup | required | 所属技能组 |
| timeout_minutes | int | required | 超时阈值 |
| action | varchar(32) | choice | `notify_only` / `transfer_to_leader` / `transfer_to_next_level` |
| notify_users | M2M→Users | | 触发时通知哪些人 |

**Unique constraint:** `(group, level)`.

### SlaPolicy 调整

| 字段 | 动作 | 说明 |
|------|------|------|
| `escalate_minutes` | **移除** | 由 `EscalationLevel.timeout_minutes` 替代 |
| 其他字段 | 保留 | `response_minutes`, `resolve_minutes` 仍用于 SLA 计算 |

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| ticket | FK→Ticket | required, db_index | 关联工单 |
| from_user | FK→Users | nullable | 转出人 (空=系统自动) |
| to_user | FK→Users | nullable | 转入人 |
| from_group | FK→SkillGroup | nullable | 转出技能组 |
| to_group | FK→SkillGroup | nullable | 转入技能组 |
| reason | text | blank | 原因 |
| transfer_type | varchar(32) | choice | `manual` / `auto_escalation` / `auto_assign` |

### Ticket 模型改动

**新增字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| category | FK→ServiceCategory (nullable) | 工单分类，供 AssignRule 路由匹配 |

**STATUS_CHOICES 扩展：**

| 原状态 | 说明 | 新增状态 | 说明 |
|--------|------|----------|------|
| draft | 草稿 | **assigned** | 已分派（等待处理人确认） |
| running | 处理中 | **receiving** | 待认领（claim-based 模式） |
| suspended | 挂起 | **escalated** | 已升级（升级触发后） |
| finished | 已完成 | | |
| terminated | 已终止 | | |
| failed | 失败 | | |

## 4. AssignEngine

### Flow

1. **Trigger:** `Ticket.submit()` or `Ticket.assign()` or creation via API.
2. **Route matching —** iterate `AssignRule` by ascending `priority`. For each rule where all non-null match fields equal the ticket's values, use `rule.target_group` and `rule.assign_mode`.
3. **Fallback —** if no rule matched, use `ticket.category.default_group` (if set and `auto_assign=true`).
4. **Person selection —** depends on `assign_mode`:
   - `to_group` — set group assignment, ticket status → `RECEIVING` (claim-based).
   - `to_onduty` — query `OnDutySchedule` for today + group; pick `primary` first, fallback to `backup`.
   - `least_busy` — count open tickets per group member (status in `[running, assigned, pending]`), assign to member with fewest.
5. **Execute —** update `Ticket.assignee` / `TicketStatus.processors`, create `TicketTransferLog(transfer_type='auto_assign')`, notify assigned user.

### Assignee storage

For the new pipeline-driven `Ticket` model, metadata is stored in `Ticket.meta`:

```json
{
  "assignee": {"id": 1, "username": "zhangsan", "name": "张三", "group": "net"},
  "assign_log": [...],
  "escalation_level": 1,
  "escalated_at": "2026-06-30T10:00:00Z"
}
```


## 5. Escalation Flow

1. **APScheduler** every 60s queries `Ticket` where status IN (running, assigned, receiving) and sla_status IN (normal, warning).
2. For each ticket, read `meta.escalation_level` (default 0 = not escalated) and `meta.escalated_at`. Baseline time: `TicketStatus.created_at` for initial level, `meta.escalated_at` for subsequent levels.
3. Find the corresponding `EscalationLevel` for the current level +1 in the ticket's assigned skill group.
4. If `now - baseline > current_level.timeout_minutes`, execute:
   - `notify_only` — send notification to `current_level.notify_users`.
   - `transfer_to_leader` — reassign to `group.leader`, log transfer.
   - `transfer_to_next_level` — increment `meta.escalation_level`, set `meta.escalated_at` = now, log transfer, notify.
5. **Record** each escalation in `TicketTransferLog(transfer_type='auto_escalation')`.

## 6. Frontend Changes

### 6.1 ITSM Ticket List (index.vue)

- **New "处理人" column** showing `assignee.name` + skill group tag.
- **Button logic:**
  - No assignee → "分派" (blue, primary).
  - Has assignee → "转派" (orange, warning) + "升级" (red, danger).
- **Assign dialog** enhanced with:
  - Skill-group filter dropdown at top.
  - Member list showing each user's current open-ticket count.
  - Quick-select by on-duty status indicator.

### 6.2 New Management Pages

| Page | Route | Description |
|------|-------|-------------|
| 技能组管理 | — | SkillGroup CRUD + member picker |
| 排班管理 | — | Calendar view to set per-user duty dates |
| 路由规则 | — | AssignRule CRUD with IF-THEN condition editor |
| 升级级别 | — | Per-skill-group escalation chain config |
| 团队看板 | — | Workload chart (pending tickets per group/member) |

All pages added as ITSM page tabs, after the existing "委托" tab.

## 7. Backend File List

### New files:
- `backend/itsm/models/skill_group.py` — SkillGroup, OnDutySchedule
- `backend/itsm/models/assign_rule.py` — AssignRule
- `backend/itsm/models/escalation.py` — EscalationLevel
- `backend/itsm/models/transfer_log.py` — TicketTransferLog
- `backend/itsm/services/assign_engine.py` — AssignEngine
- `backend/itsm/services/escalation_service.py` — EscalationService
- `backend/itsm/management/commands/start_itsm_scheduler.py` — APScheduler process entry
- `backend/itsm/views/assign_views.py` — ModelViewSets for new models
- `backend/itsm/serializers/assign_serializers.py` — Serializers

### Modified files:
- `backend/itsm/models/incident.py` — add `default_group`, `auto_assign` to ServiceCategory; remove `SlaPolicy.escalate_minutes`
- `backend/itsm/models/ticket.py` — add `category` FK, expand `STATUS_CHOICES`
- `backend/itsm/urls.py` — register new routes
- `backend/itsm/views/ticket_views.py` — integrate AssignEngine into assign/submit actions

## 8. Frontend File List

### New files:
- `web/src/views/apps/itsm/SkillGroup.vue`
- `web/src/views/apps/itsm/OnDutySchedule.vue`
- `web/src/views/apps/itsm/AssignRule.vue`
- `web/src/views/apps/itsm/EscalationLevel.vue`
- `web/src/views/apps/itsm/TeamDashboard.vue`

### Modified files:
- `web/src/views/apps/itsm/index.vue` — new columns, assign dialog, tab entries
- `web/src/api/itsm/index.ts` — new API functions
