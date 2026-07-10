# SLA Working Time Model — Design Spec

> **Date:** 2026-07-10
> **Status:** Design Complete (pending approval)
> **Reference:** BK-ITSM Schedule + Day + Duration model

---

## Context

OpsFlow ITSM 当前的 SLA 引擎使用纯自然时间计算 deadline（`now + timedelta(minutes=N)`），不支持工作时间/假期/加班的概念。这导致 SLA 计时不准确：例如周五 17:30 来的 P1 工单，1 小时响应期限会算出周五 18:30 截止——但此时已下班，实际没人处理。

BK-ITSM 有一套成熟的三层工作时间模型（Schedule → Day → Duration），支持工作时段定义、假期排除、加班日补充。本设计将这套模型完整引入 OpsFlow ITSM，实现企业级 SLA 时间计算。

此外，当前代码中存在两个已知缺陷一并修复：
1. `SlaEngine.start_ticket_sla()` 中 response_minutes / resolve_minutes 变量名互换（bug）
2. `EscalationLevel` 模型定义了完整的升级动作但 `SlaEngine._execute_escalation()` 硬编码了通知，完全未调用

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 实现深度 | 完整版（Schedule + Day + Duration + 假期日历 UI） | 用户明确选择 |
| Schedule 作用域 | 全局 + 项目级（project FK nullable） | 对齐现有 SlaPolicy project 隔离模式 |
| SlaPolicy 改造 | 完全替换模型（BK-ITSM PriorityPolicy 结构） | 用户明确选择，不保留旧兼容 |
| 前端 | 完整 UI（Schedule 管理页 + 假期日历 + SlaPolicy 编辑改造） | 用户明确选择 |
| 实施方式 | 全量一次交付（方案 B） | 用户明确选择 |

---

## 1. Data Models

### 1.1 Duration（工作时间段）

```
File: backend/itsm/models/schedule.py (NEW)

Duration(CoreModel):
    name = CharField(128)           # "上午班"
    name_en = CharField(128)        # "Morning"
    start_time = TimeField          # 09:00:00
    end_time = TimeField            # 12:00:00
```

### 1.2 Day（日期定义）

```
Day(CoreModel):
    name = CharField(128)           # "标准工作日"
    name_en = CharField(128)        # "Weekday"
    day_of_week = CharField(32, default='-1')  # "0,1,2,3,4" (0=Mon, 6=Sun)
    type_of_day = CharField(choices: NORMAL | WORKDAY | HOLIDAY)
    start_date = DateField(null=True)   # for WORKDAY/HOLIDAY ranged
    end_date = DateField(null=True)
    durations = M2M → Duration      # working time segments for this day

    - NORMAL: uses day_of_week to match weekdays → applies durations
    - WORKDAY: uses start_date~end_date range → adds durations (overtime)
    - HOLIDAY: uses start_date~end_date range → excludes from working time
```

### 1.3 Schedule（排班表）

```
Schedule(CoreModel):
    name = CharField(128)
    name_en = CharField(128)
    project = FK → iam.Project (null=True = global)
    is_builtin = BooleanField(default=False)  # cannot delete builtin
    days = M2M → Day, related_name='schedule_days'       # NORMAL days
    workdays = M2M → Day, related_name='schedule_workdays' # WORKDAY
    holidays = M2M → Day, related_name='schedule_holidays' # HOLIDAY
```

**Built-in seeds (auto-created by migration):**

| Schedule | Day | Durations |
|----------|-----|-----------|
| "5×8 标准" | NORMAL, day_of_week="0,1,2,3,4" | [08:00-12:00, 14:00-18:00] |
| "7×24" | NORMAL, day_of_week="0,1,2,3,4,5,6" | [00:00-23:59] |

### 1.4 SlaPolicy（重构）

```
SlaPolicy(CoreModel):  # in catalog.py — COMPLETELY REPLACED
    name = CharField(128)
    name_en = CharField(128)
    project = FK → iam.Project (null=True)
    priority = CharField(choices: P1/P2/P3/P4)
    schedule = FK → Schedule, on_delete=PROTECT  # REQUIRED (null=False)

    # REPLACE: response_minutes → response_time + response_unit
    response_time = IntegerField(default=60)
    response_unit = CharField(choices: m/h/d, default='m')

    # REPLACE: resolve_minutes → resolve_time + resolve_unit
    resolve_time = IntegerField(default=480)
    resolve_unit = CharField(choices: m/h/d, default='m')

    escalation_levels = M2M → EscalationLevel (blank=True)  # NEW
    is_active = BooleanField(default=True)

    class Meta:
        unique_together = ('priority', 'schedule', 'project')
        # Note: nullable project causes NULL != NULL in SQL.
        # Application-level uniqueness enforced in SlaPolicySerializer.validate().
```

### 1.5 SlaTask（新增字段）

```
SlaTask:  # in sla.py — ADD 3 fields
    # Existing fields unchanged...
    cost_time = IntegerField(default=0)       # NEW: effective SLA seconds consumed
    total_seconds = IntegerField(default=0)   # NEW: frozen total SLA seconds at creation
    begin_at = DateTimeField(null=True)       # NEW: when SLA task started
```
`total_seconds` is frozen at creation (resolve_time converted to seconds) so resume
can compute `remaining = total_seconds - cost_time` without relying on the policy
(which may have been modified since creation).

### 1.6 Timezone

All Duration times are naive `TimeField` values. SlaTime combines them with dates
using `django.conf.settings.TIME_ZONE` (Asia/Shanghai) to produce timezone-aware
datetimes via `timezone.make_aware(datetime.combine(date, duration.start_time))`.

### 1.7 Model Validation

| Model | Rule |
|-------|------|
| Day | NORMAL type → `day_of_week` required, `start_date`/`end_date` must be null |
| Day | WORKDAY/HOLIDAY type → `start_date`/`end_date` required, `day_of_week` ignored |
| Schedule | Must have ≥1 NORMAL day with ≥1 Duration, otherwise no working time exists |
| Schedule | is_builtin=True → delete blocked at ViewSet level (not model, for admin safety) |

---

## 2. SlaTime Engine

```
File: backend/itsm/services/sla_time.py (NEW, ~250 lines)
```

### 2.1 TimeDelta — Single Interval

```python
class TimeDelta:
    """Single datetime interval with set-theoretic operations."""
    def __init__(self, start_time, end_time): ...
    def seconds(self) → int
    def intersection(self, other) → TimeDelta | None
    def difference(self, other) → [TimeDelta]     # returns list (0, 1, or 2 segments)
    def union(self, other) → [TimeDelta]          # merges if overlapping
    def is_intersect(self, other) → bool
    def position(self, time) → -1 | 0 | 1        # left / inside / right
    def date_list(self) → [date]                  # all dates spanned
```

### 2.2 MultiTimeDelta — Multi-Interval Algebra

```python
class MultiTimeDelta:
    """Collection of non-overlapping TimeDelta intervals."""
    def __init__(self, *time_deltas): ...
    def intersection(self, other: MultiTimeDelta) → MultiTimeDelta
    def difference(self, other: MultiTimeDelta) → MultiTimeDelta
    def union(self, other: MultiTimeDelta) → MultiTimeDelta
    def closest_td_time(self, time, is_forward: bool) → datetime | None
    def sort(self) → MultiTimeDelta
```

### 2.3 SlaTime — Core Calculator

```python
class SlaTime:
    def __init__(self, schedule, sla_policy):
        """Pre-fetch schedule → days/workdays/holidays → durations into dict."""

    def date_time_deltas(self, date) → [TimeDelta]:
        """Working intervals for a given date.
        1. Match NORMAL Day by date.weekday() → get Durations as TimeDeltas
        2. If holidays cover date → difference(working, holiday)
        3. If workdays cover date → union(result, workday)
        """

    def sla_time(self, start, end) → int:
        """Effective SLA seconds between two datetimes (working-time only)."""

    def sla_deadline(self, start_time, sla_seconds) → datetime:
        """Wall-clock deadline after consuming sla_seconds of working time.
        Iterative: find next SLA boundary → advance → recalculate consumed → recurse.
        """
```

**Key algorithm detail — `sla_deadline` iterative approach:**
1. Start from start_time with remaining = sla_seconds
2. Find next SLA time boundary forward via `closest_td_time()`
3. Advance cursor by min(remaining, natural_seconds_to_boundary)
4. Recalculate actual SLA seconds consumed via `sla_time(start_time, cursor)`
5. Subtract consumed from remaining; if remaining > 0, repeat from step 2
6. Return cursor when remaining reaches 0

This naturally handles crossing weekends, holidays, and gap periods.

---

## 3. SlaEngine Refactoring

```
File: backend/itsm/services/sla_engine.py (MODIFY)
```

### 3.1 start_ticket_sla() — Changes

1. **Fix swap bug:** `response_time` → `reply_deadline`, `resolve_time` → `deadline`
2. **Use SlaTime:** Instead of `now + timedelta(minutes=N)`, call `SlaTime(schedule, policy).sla_deadline(now, sla_seconds)`
3. **Convert units to seconds** before passing: m×60, h×3600, d×86400
4. **Freeze total_seconds:** Store `resolve_time_in_seconds` as `task.total_seconds`
5. **Set begin_at:** `task.begin_at = now`

### 3.2 pause_ticket_sla() — Changes

- Before pause: calculate `cost_time = SlaTime.sla_time(begin_at, now)` and save on SlaTask
- This records effective SLA seconds consumed (not wall-clock time)

### 3.3 resume_ticket_sla() — Changes

- New approach: recalculate deadline from now using **remaining sla_seconds**
  - `remaining = task.total_seconds - task.cost_time`
  - `new_deadline = SlaTime.sla_deadline(now, remaining)`
- Replace old approach of simply shifting deadline by pause duration (which breaks across weekends)
- Reset `begin_at = now` so subsequent cost_time calculations are correct

### 3.4 check_all_active_sla() — Changes

Before checking violations, update cost_time for each running task:
```python
for task in active_tasks:
    if task.begin_at:
        task.cost_time = SlaTime(task.sla_policy.schedule, task.sla_policy
                                 ).sla_time(task.begin_at, now)
        task.save(update_fields=['cost_time'])
```
Then use `task.cost_time` (not just `now > deadline`) when evaluating escalation levels.

### 3.5 _execute_escalation() — Changes

Replace hardcoded notification with EscalationLevel query:

```python
def _execute_escalation(ticket, sla_task):
    levels = sla_task.sla_policy.escalation_levels.filter(is_active=True).order_by('level')
    for level in levels:
        if sla_task.cost_time >= level.timeout_minutes * 60:
            if level.action == 'notify_only':
                NotificationService.notify_sla_violation(ticket)
            elif level.action == 'transfer_leader':
                leader = resolve_leader(ticket.processor)
                ticket.assign(leader)
            elif level.action == 'transfer_next':
                escalate_to_next_level(ticket)
            elif level.action == 'notify_users':
                notify_specific_users(level.notify_users.split(','))
```

---

## 4. API Layer

### 4.1 New Endpoints

| Endpoint | ViewSet | File |
|----------|---------|------|
| `GET/POST /api/itsm/schedules/` | ScheduleViewSet | `views/schedule_views.py` (NEW) |
| `GET/PUT/DELETE /api/itsm/schedules/{id}/` | ↑ | ↑ |
| `GET/POST /api/itsm/days/` | DayViewSet | ↑ |
| `GET/PUT/DELETE /api/itsm/days/{id}/` | ↑ | ↑ |
| `GET/POST /api/itsm/durations/` | DurationViewSet | ↑ |
| `GET/PUT/DELETE /api/itsm/durations/{id}/` | ↑ | ↑ |

All ViewSets extend `ItsmProjectViewSet` for project-scoped filtering.

### 4.2 Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `CRUD /api/itsm/sla-policies/` | Serializer: schedule FK, response/resolve time+unit, escalation_levels M2M. **Serializer validate()**: unique_together('priority','schedule','project') enforced at app level (nullable project cannot use DB constraint). ViewSet filter_fields: add `'schedule'`. |
| `GET /api/itsm/tickets/` | `get_sla_info()` in TicketSerializer: remaining_seconds now uses `SlaTime.sla_time(now, task.deadline)` for SLA-effective remaining time, not natural time. |
| `GET /api/itsm/dashboard/summary/` + `overdue/` | No schema change. `overdue_seconds` calculation unchanged (wall-clock overdue is still informative). |

### 4.3 Key Serializer Details

**ScheduleSerializer:** Nested writes — separate M2M fields for days/workdays/holidays via `PrimaryKeyRelatedField(many=True, write_only=True)`.

**DaySerializer:** Include `duration_ids` for write, nest Duration data for read.

**SlaPolicySerializer:** Replace `response_minutes`/`resolve_minutes` with `response_time`+`response_unit`/`resolve_time`+`resolve_unit`. Add `schedule` (required) and `escalation_level_ids`.

---

## 5. Frontend

### 5.1 New Components

| Component | Purpose |
|-----------|---------|
| `ScheduleList.vue` | New tab in ITSM index page. Table listing schedules with name, working days count, project scope, actions. Create/Edit dialog. |
| `ScheduleEdit.vue` | Dialog inside ScheduleList. Form: name, project selector, three sub-tables for NORMAL/WORKDAY/HOLIDAY days. Each Day row expands to Duration segments. |
| `HolidayCalendar.vue` | Embedded in ScheduleEdit for holiday Day rows. Date range picker with visual calendar highlighting selected ranges. |

### 5.2 Modified Components

| Component | Change |
|-----------|--------|
| `SlaPolicyList.vue` | Add: schedule dropdown selector, response/resolve time + unit fields (number input + select), escalation_levels multi-select, CREATE button (currently missing). Remove: response_minutes/resolve_minutes number inputs. |

### 5.3 Routing

No new routes. Schedule management is a new tab (`schedule`) in the existing ITSM index page, same pattern as current `sla` and `escalation` tabs.

### 5.4 i18n

All new UI text goes through vue-i18n. New keys under `message.itsmPage.schedule.*` namespace, covering: schedule list title, day type labels (NORMAL/WORKDAY/HOLIDAY), duration editor, holiday date picker, time unit labels. Both zh-CN and en translations required.

### 5.5 API Client

Add to `web/src/api/itsm/index.ts`:
```typescript
export const scheduleApi = createCrudApi('schedules')
export const dayApi = createCrudApi('days')
export const durationApi = createCrudApi('durations')
```

---

## 6. Migration Plan

### 6.1 Migration Operations (in order)

1. CreateModel: Duration
2. CreateModel: Day (M2M → Duration)
3. CreateModel: Schedule (M2M → Day × 3)
4. RunPython: `seed_builtin_schedules()` — create "5×8" and "7×24" with is_builtin=True
5. RemoveField: SlaPolicy.response_minutes
6. RemoveField: SlaPolicy.resolve_minutes
7. AddField: SlaPolicy.schedule (FK → Schedule, null=True initially)
8. AddField: SlaPolicy.response_time (int, default=60)
9. AddField: SlaPolicy.response_unit (char, default='m')
10. AddField: SlaPolicy.resolve_time (int, default=480)
11. AddField: SlaPolicy.resolve_unit (char, default='m')
12. AddField: SlaPolicy.escalation_levels (M2M → EscalationLevel, blank=True)
13. RunPython: `migrate_existing_policies()`
    - For each existing SlaPolicy: schedule='7×24', response_time=old.response_minutes, response_unit='m', resolve_time=old.resolve_minutes, resolve_unit='m'
14. AlterField: SlaPolicy.schedule (null=False)
15. RemoveField: SlaPolicy.priority unique=True (replaced by unique_together)
16. AddField: SlaTask.cost_time (int, default=0)
17. AddField: SlaTask.total_seconds (int, default=0)
18. AddField: SlaTask.begin_at (DateTimeField, null=True)
19. AddConstraint: unique_together('priority', 'schedule', 'project') on SlaPolicy

### 6.2 Rollback Safety

- RunPython operations have `reverse_code` for reversibility
- Existing running SLA tasks continue to work: "7×24" schedule behavior is identical to old natural-time (00:00-23:59 × 7 days = full coverage)
- No data loss: old response_minutes/resolve_minutes values mapped 1:1 to new time/unit fields

---

## 7. Test Plan

### 7.1 Unit Tests (sla_time.py)

| ID | Test | Verify |
|----|------|--------|
| T1 | TimeDelta.intersection/difference/union | Set ops correct for overlapping/adjacent/disjoint intervals |
| T2 | MultiTimeDelta.difference(MultiTimeDelta) | Multi-interval subtraction across 3+ segments |
| T3 | date_time_deltas: weekday match | Monday returns [08:00-12:00, 14:00-18:00] for 5×8 |
| T4 | date_time_deltas: holiday exclusion | Oct 1 (holiday) returns empty for 5×8 |
| T5 | date_time_deltas: overtime inclusion | Saturday marked WORKDAY returns working hours |
| T6 | sla_time: across weekend | Fri 17:00 → Mon 10:00 counts only Fri 17-18 + Mon 08-10 = 3h |
| T7 | sla_deadline: 5×8, 2h task at Fri 17:30 | → Mon 09:30 |
| T8 | sla_deadline: 7×24, 2h task | → Fri 19:30 (same as natural time) |
| T9 | sla_deadline: 5×8 with holiday (Oct 1-3) | Skips holiday dates correctly |
| T10 | date_time_deltas: WORKDAY (Sat marked overtime) | Saturday has working hours from workday Durations |

### 7.2 Integration Tests (sla_engine.py)

| ID | Test | Verify |
|----|------|--------|
| T11 | start_ticket_sla with schedule | Deadline uses SlaTime, total_seconds + begin_at set |
| T12 | pause/resume preserves correct deadline | Pause Fri 17:00, resume Mon 09:00 → deadline recalculated correctly |
| T13 | check_all_active_sla updates cost_time | Running tasks get cost_time refreshed before escalation check |
| T14 | _execute_escalation: notify_only | NotificationService called on violation |
| T15 | _execute_escalation: transfer_leader | resolve_leader + assign called |
| T16 | response_time → reply_deadline (swap fix) | Correct field mapping |
| T17 | Schedule CRUD API | Create, list, update, delete all work |
| T18 | Builtin schedule block | Cannot delete is_builtin=True schedule |
| T19 | SlaPolicy unique validation | Duplicate priority+schedule+project rejected by serializer |
| T20 | Migration: existing policy → 7×24 | Data integrity post-migrate |

### 7.3 Manual Verification

| Step | Action | Expected |
|------|--------|----------|
| V1 | Create Schedule "5×8" in UI | Appears in list, editable |
| V2 | Add holiday Day (Oct 1-7) | HolidayCalendar shows range highlighted |
| V3 | Create SlaPolicy with 5×8 schedule | Save succeeds |
| V4 | Create P1 ticket at Fri 17:30 | Deadline = Mon morning |
| V5 | Suspend ticket, wait, resume | Deadline recalculates correctly |
| V6 | SLA violation → escalation triggers | Notification sent, action executed |
| V7 | TicketDetail SLA card | Displays correct deadline + remaining time |

---

## 8. Files Summary

### New Files (8)
| File | Purpose |
|------|---------|
| `backend/itsm/models/schedule.py` | Duration, Day, Schedule models |
| `backend/itsm/services/sla_time.py` | TimeDelta, MultiTimeDelta, SlaTime |
| `backend/itsm/serializers/schedule.py` | Schedule, Day, Duration serializers |
| `backend/itsm/views/schedule_views.py` | Schedule, Day, Duration ViewSets |
| `backend/itsm/tests/test_sla_time.py` | SlaTime unit + integration tests |
| `web/src/views/apps/itsm/components/ScheduleList.vue` | Schedule management page |
| `web/src/views/apps/itsm/components/ScheduleEdit.vue` | Schedule edit dialog |
| `web/src/views/apps/itsm/components/HolidayCalendar.vue` | Holiday date range picker |

### Modified Files (12)
| File | Change |
|------|--------|
| `backend/itsm/models/catalog.py` | Refactor SlaPolicy model |
| `backend/itsm/models/sla.py` | Add cost_time, total_seconds, begin_at to SlaTask |
| `backend/itsm/models/__init__.py` | Export new models |
| `backend/itsm/services/sla_engine.py` | SlaTime integration + escalation wiring + bug fix + check_all_active_sla cost update |
| `backend/itsm/serializers/legacy.py` | Update SlaPolicySerializer (schedule + time/unit + escalation_levels + unique validation) |
| `backend/itsm/serializers/ticket_serializers.py` | Update get_sla_info() for SLA-effective remaining time |
| `backend/itsm/views/views.py` | SlaPolicyViewSet: add 'schedule' to filter_fields |
| `backend/itsm/urls.py` | Register new Schedule/Day/Duration ViewSets |
| `web/src/api/itsm/index.ts` | Add schedule/day/duration API clients |
| `web/src/views/apps/itsm/index.vue` | Add schedule tab |
| `web/src/views/apps/itsm/components/SlaPolicyList.vue` | Add schedule + time/unit fields + create button |
| `web/src/i18n/pages/itsm/{zh-cn,en}.ts` | Add schedule i18n keys |

### Removed (0)
No files are removed. Old SlaPolicy fields are replaced in-place via migration.

---

## 9. Verification

After implementation, verify end-to-end:

1. `python manage.py migrate` — migration runs cleanly (19 operations)
2. `python manage.py test itsm.tests.test_sla_time` — all 20 tests pass
3. Create a Schedule with holidays in UI → saves and displays correctly
4. Create SlaPolicy with that schedule → ticket SLA deadline respects working hours
5. TicketDetail SLA card shows SLA-effective remaining time (not natural time)
6. Suspend/resume preserves correct deadline across non-working periods
7. SLA violation triggers EscalationLevel actions in order
8. Delete a Schedule referenced by SlaPolicy → PROTECT blocks deletion
