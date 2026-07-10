# Change Calendar Design — 变更日历

> **Date:** 2026-07-10
> **Status:** Design Approved
> **Priority:** P2 — 变更时间线展示，当前无前端组件

---

## Context

ITSM 变更工单和 OpsFlow 定时执行计划各自独立展示，用户缺少一个统一的"什么时候会发生什么变更"视图。本设计引入变更日历，聚合 ITSM Ticket + OpsFlow SchedulePlan 两种数据源，提供日历月/周视图和时间线列表两种模式，点击弹出详情卡片。

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 数据来源 | ITSM Ticket + OpsFlow SchedulePlan | 审批驱动的计划变更 + 时间驱动的自动变更，构成完整图景 |
| 后端数据层 | 后端聚合 API（新端点） | 日历是日期驱动的查询，后端排序合并比分页返回更合理；符合项目 `dashboard/stats/` 聚合模式 |
| 视图模式 | 月视图/周视图 + 时间线列表，Tab 切换 | 月视图看分布，时间线看顺序，Google Calendar 式双模式 |
| 点击交互 | el-popover 详情卡片 + "查看详情"跳转链接 | 快速预览 + 深度导航，Google Calendar 式交互 |
| 筛选维度 | 来源 + 工单类型；优先级用颜色 | 优先级筛选不如颜色直观；来源切换是关键区分 |
| Hero 数据流 | useHeroProvider/useHeroConsumer，子 tab 各自 reportStats() | 沿用项目现有模式，保持一致性 |
| View 基类 | `ItsmProjectViewSet` | Ticket 有直接 `project` FK（`itsm_ticket.project`），自动 filter 可用 |

---

## 1. Data Sources

Two existing models supply all data — no new models required:

| Source | Model | project FK | Time Fields | Key Attributes |
|--------|-------|-----------|-------------|----------------|
| ITSM Ticket | `itsm_ticket` | `project` (FK→iam.Project, SET_NULL) | `created_at`, `finished_at`, SLA deadline | sn, title, status, priority (P1-P4), service_item, assignee, ticket_type |
| OpsFlow SchedulePlan | `opsflow_schedule_plan` | `project` (FK→iam.Project, CASCADE) | `scheduled_at`, `next_run_at`, `last_run_at` | name, status, cron_expr, cron_description |

**Time window mapping for ITSM tickets** (until a dedicated "planned change window" field is added):
- `start_time` → `created_at`
- `end_time` → SLA deadline (if SLA policy exists) or `finished_at` (if completed); unresolved tickets use `created_at` + estimated duration

**Time window mapping for SchedulePlan:**
- `start_time` → `scheduled_at` (one-time) or `next_run_at` (cron)
- `end_time` → `start_time` + estimated execution duration

---

## 2. API Design

### 2.1 Endpoint

```
GET /api/itsm/change-calendar/
```

### 2.2 Query Parameters

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `start_date` | date | yes | Range start (ISO 8601) |
| `end_date` | date | yes | Range end |
| `project_id` | int | yes | Project-scoped (auto-filtered via `ItsmProjectViewSet` on Ticket; manual filter on SchedulePlan) |
| `source` | str | no | `itsm_ticket`, `opsflow_schedule`, or absent for all |
| `ticket_type` | str | no | `change`, `incident`, `request`, `problem` — only applies when source includes ITSM |

### 2.3 Response Format

```json
{
  "code": 2000,
  "data": {
    "items": [
      {
        "id": "ticket_42",
        "source": "itsm_ticket",
        "title": "核心交换机固件升级",
        "ticket_sn": "ITSM20260710-143052",
        "status": "running",
        "status_display": "审批中",
        "priority": "P1",
        "start_time": "2026-07-10T08:00:00Z",
        "end_time": "2026-07-10T10:00:00Z",
        "link": "/apps/itsm/ticket/42",
        "assignee": ["张三", "李四"],
        "service_item_name": "网络变更",
        "sla_deadline": "2026-07-12T18:00:00Z"
      },
      {
        "id": "schedule_7",
        "source": "opsflow_schedule",
        "title": "每周数据备份",
        "status": "active",
        "status_display": "运行中",
        "priority": null,
        "start_time": "2026-07-10T02:00:00Z",
        "end_time": "2026-07-10T02:30:00Z",
        "link": "/apps/opsflow-template/schedule/7",
        "cron_description": "每天凌晨2:00"
      }
    ],
    "total": 15
  }
}
```

- `id` includes source prefix to prevent key collisions
- Fields vary by source — frontend renders conditionally on `source`
- `priority` is null for SchedulePlan items; calendar renders them with a distinct color

### 2.4 Backend Implementation

```
itsm/views/change_calendar.py   → ChangeCalendarView(ItsmProjectViewSet)
itsm/services/change_calendar.py → ChangeCalendarService.aggregate(start, end, project_id, source, ticket_type)
itsm/serializers/change_calendar.py → CalendarItemSerializer
```

The service:
1. Queries `Ticket.objects.filter(project_id=..., created_at__gte=start, created_at__lte=end)` (project auto-filtered by `ItsmProjectViewSet`)
2. Queries `SchedulePlan.objects.filter(project_id=..., scheduled_at__range=(start, end))` (manual project filter)
3. Normalizes both into a unified dict format
4. Merges and sorts by `start_time`
5. Returns sorted list

Cross-app model access (`from opsflow.models import SchedulePlan`) is permitted per project architecture rules.

---

## 3. Frontend Architecture

```
views/apps/itsm/
  ChangeCalendar.vue            ← parent page (hero + filter bar + tabs)
  components/
    CalendarView.vue            ← month/week grid (el-table + span-method, inspired by DutyCalendar.vue)
    TimelineView.vue            ← grouped timeline list (inspired by TicketDetail.vue custom timeline)
    ChangeDetailPopover.vue     ← popover card on item click
```

### 3.1 Parent Page (ChangeCalendar.vue)

- Follows hero section pattern: `@include g-hero-container`, `useHeroProvider()`
- Hero displays: total changes in range, by-source count, upcoming this week
- Hero stats are reported by child tabs via `useHeroConsumer().reportStats(items)` — CalendarView and TimelineView each call it on their data load
- Below hero: filter bar + view toggle button group (月视图 / 周视图 / 列表)
- Tab lazy-loading via `useTabLazyLoad`:
  ```html
  <div v-if="isVisited('calendar')" v-show="activeTab === 'calendar'" class="app-section">
    <CalendarView :active="activeTab === 'calendar'" />
  </div>
  <div v-if="isVisited('timeline')" v-show="activeTab === 'timeline'" class="app-section">
    <TimelineView :active="activeTab === 'timeline'" />
  </div>
  ```

### 3.2 Filters

| Control | Type | Values |
|---------|------|--------|
| Source | el-select | 全部 / ITSM工单 / 定时计划 |
| Ticket Type | el-select | 全部 / 变更 / 事件 / 服务请求 / 问题 (visible only when source includes ITSM) |
| Month Navigation | ← → arrow buttons + "今天" button | Month/Week paging; "今天" snaps to current date |

Priority is NOT a filter — it is expressed as a colored left border on calendar items:
- P1 = red (`#F56C6C`), P2 = orange (`#E6A23C`), P3 = blue (`#409EFF`), P4 = gray (`#909399`)
- SchedulePlan items = purple (`#A855F7`)

### 3.3 UI States

| State | Behavior |
|-------|----------|
| **Loading** | el-skeleton / v-loading on the calendar area while API fetches |
| **Empty** | el-empty with message "暂无变更" / "No changes" |
| **Error** | ElMessage.error with API error message; retry button in empty state area |
| **Normal** | Calendar grid or timeline list rendered with data |

---

## 4. Calendar View (CalendarView.vue)

### 4.1 Layout

- Uses `el-table` with 7 columns: 一(Mon) / 二(Tue) / 三(Wed) / 四(Thu) / 五(Fri) / 六(Sat) / 日(Sun)
- **Monday is week start** (China locale)
- Reference implementation: `web/src/views/apps/monitor/DutyCalendar.vue`
- Month view: default, ~5-6 rows based on month layout
- Week view: single row, 7 columns spanning full cell height
- Header row shows abbreviated day names (一/二/三/四/五/六/日)
- Date numbers in top-left corner of each cell; "today" cell has highlighted background
- "今天" (Today) button in the navigation bar snaps to current month/week

### 4.2 Item Rendering

Each calendar cell renders compact colored bars:

```
┌──────────────────────────┐
│ 🔴 核心交换机固件升级 P1   │  ← left color stripe = priority
│ 🟣 每周数据备份            │  ← purple = schedule
│ +2 more                  │  ← collapse overflow
└──────────────────────────┘
```

- Bar: 2px left color border + truncated title + priority badge
- Max 3 items visible per cell; overflow shows "+N more" expander that opens a mini-list popover
- Items spanning multiple days render across cells via `span-method`
- Single-day items render as compact bars within the cell

### 4.3 Cross-Day Items

For items where `start_time` and `end_time` span multiple days, `span-method` merges cells horizontally. The bar renders across the merged cell with gradient fade at edges.

---

## 5. Timeline View (TimelineView.vue)

### 5.1 Layout

- Grouped by date (descending), each day a visual block with a sticky date header
- Within each day: chronological list of items
- Reference: `TicketDetail.vue` custom timeline CSS (`.td-timeline-*` classes, manual dot + connecting line)
- Scrollable list with lazy-load (load more on scroll past 50 items)

### 5.2 Item Row

```
● 08:00 ─────────── 12:00
  🔴 核心交换机固件升级  P1  审批中  张三,李四
  ITSM20260710-143052  网络变更
```

- Left side: vertical timeline line + colored dot (red=P1, orange=P2, blue=P3, gray=P4, purple=schedule)
- Time bar: start–end time range with a light background bar indicating duration proportion
- Row 1: title + priority badge + status tag + assignee chips
- Row 2: ticket SN + service item name (ITSM) or cron description (SchedulePlan)

---

## 6. Detail Popover (ChangeDetailPopover.vue)

Triggered on click of any calendar/timeline item. Uses `el-popover` with `trigger="click"`, placement auto.

### 6.1 ITSM Ticket Card

```
┌─────────────────────────┐
│ 核心交换机固件升级    🔴P1│
│ ═══════════════════════ │
│ 📋 ITSM20260710-143052   │
│ 📂 网络变更 / 核心网络    │
│ ⏰ 2026-07-10 08:00~12:00│
│ 📊 状态: 审批中           │
│ 👤 处理人: 张三, 李四      │
│ ⏳ SLA截止: 2026-07-12    │
│ ─────────────────────── │
│        [查看详情 →]       │  ← router-link to /apps/itsm/ticket/:id
└─────────────────────────┘
```

### 6.2 SchedulePlan Card

```
┌─────────────────────────┐
│ 每周数据备份          🟣定时│
│ ═══════════════════════ │
│ ⏰ 2026-07-10 02:00~02:30│
│ 📊 状态: 运行中           │
│ 🔄 频率: 每天凌晨2:00     │
│ 📋 关联模板: 数据库备份    │
│ ─────────────────────── │
│        [查看详情 →]       │  ← router-link to schedule detail
└─────────────────────────┘
```

- Card renders conditionally on `source` field — different metadata per source type
- Popover closes on: click outside, Escape key, or clicking "查看详情" link

---

## 7. Route & Menu

- Route path: `/apps/itsm/change-calendar`
- Menu label: `变更日历` (zh) / `Change Calendar` (en)
- Menu icon: `Calendar` from `@element-plus/icons-vue`
- Placed under ITSM menu group
- Uses `ItsmProjectViewSet` for project isolation (Ticket has direct `project` FK)
- Menu entry added via `seed_iam_page_configs.py` for backend-controlled routing

---

## 8. i18n

New translation keys under `message.changeCalendar.*` in both `zh-cn.ts` and `en.ts`:

| Key | zh | en |
|-----|----|----|
| `title` | 变更日历 | Change Calendar |
| `monthView` | 月视图 | Month |
| `weekView` | 周视图 | Week |
| `listView` | 列表 | List |
| `today` | 今天 | Today |
| `sourceAll` | 全部 | All |
| `sourceTicket` | ITSM工单 | ITSM Ticket |
| `sourceSchedule` | 定时计划 | Schedule |
| `ticketType` | 工单类型 | Ticket Type |
| `ticketTypeChange` | 变更申请 | Change |
| `ticketTypeIncident` | 事件工单 | Incident |
| `ticketTypeRequest` | 服务请求 | Request |
| `ticketTypeProblem` | 问题管理 | Problem |
| `viewDetail` | 查看详情 | View Details |
| `noItems` | 暂无变更 | No changes |
| `loadError` | 加载失败，请重试 | Load failed, please retry |
| `retry` | 重试 | Retry |
| `totalChanges` | 变更总数 | Total Changes |
| `upcomingWeek` | 本周待执行 | Upcoming This Week |
| `slaDeadline` | SLA截止 | SLA Deadline |
| `cronDesc` | 执行频率 | Frequency |
| `status` | 状态 | Status |
| `priority` | 优先级 | Priority |
| `assignee` | 处理人 | Assignee |
| `serviceItem` | 服务项 | Service Item |
| `moreItems` | 更多 | more |

---

## 9. Files Summary

### New Files (7)

| File | Purpose |
|------|---------|
| `backend/itsm/views/change_calendar.py` | `ChangeCalendarView(ItsmProjectViewSet)` — list endpoint |
| `backend/itsm/services/change_calendar.py` | `ChangeCalendarService.aggregate()` — cross-source aggregation |
| `backend/itsm/serializers/change_calendar.py` | `CalendarItemSerializer` — unified response format |
| `web/src/views/apps/itsm/ChangeCalendar.vue` | Parent page (hero + filter bar + tab switching) |
| `web/src/views/apps/itsm/components/CalendarView.vue` | Month/week grid view |
| `web/src/views/apps/itsm/components/TimelineView.vue` | Grouped timeline list view |
| `web/src/views/apps/itsm/components/ChangeDetailPopover.vue` | Click-triggered detail popover card |

### Modified Files (5)

| File | Change |
|------|--------|
| `backend/itsm/urls.py` | Register `change-calendar/` route |
| `web/src/api/itsm/index.ts` | Add `getChangeCalendar(params)` API client |
| `web/src/i18n/pages/itsm/zh-cn.ts` | Add `message.changeCalendar.*` keys |
| `web/src/i18n/pages/itsm/en.ts` | Add `message.changeCalendar.*` keys |
| `backend/iam/management/commands/seed_iam_page_configs.py` | Add change-calendar page permission (or front-end route if using frontEnd.ts) |

### Removed (0)

No files removed.

---

## 10. Test Plan

### API Tests

| ID | Test | Verify |
|----|------|--------|
| A1 | GET with valid date range + project | Returns 200, items array sorted by start_time |
| A2 | GET with `source=itsm_ticket` | Only ITSM ticket items returned |
| A3 | GET with `source=opsflow_schedule` | Only SchedulePlan items returned |
| A4 | GET with `ticket_type=change` | Only change-type tickets returned |
| A5 | Empty date range (no changes) | Returns 200, items=[], total=0 |
| A6 | Missing required params | Returns 400 |
| A7 | Project isolation | Different project_id returns disjoint sets |
| A8 | Cross-day item | Item with start/end spanning 3 days appears correctly with full time range |
| A9 | SchedulePlan without project | schedule items with null project appear when project_id matches or filter handles null |

### Frontend Tests

| ID | Test | Verify |
|----|------|--------|
| F1 | Calendar month view renders | 7-column grid, Mon-first, items in correct date cells |
| F2 | Priority color mapping | P1=red, P2=orange, P3=blue, P4=gray, schedule=purple |
| F3 | Week view toggle | Switches to single-row 7-column view |
| F4 | Timeline view | Items grouped by date, chronological within day |
| F5 | Popover on click | Click item → popover with correct metadata per source type |
| F6 | "查看详情" link | Router navigates to correct detail page |
| F7 | Source filter | Switch source → re-fetch with correct param |
| F8 | Ticket type filter visibility | Shows only when source includes ITSM |
| F9 | "今天" button | Snaps calendar to current date |
| F10 | Month navigation arrows | ← → flips month correctly |
| F11 | Empty state | el-empty shown when no items |
| F12 | Loading state | v-loading shown during API fetch |
| F13 | Error state | ElMessage.error + retry option |
| F14 | i18n switch | All labels, statuses update on language change |
| F15 | Hero stats | Total changes + upcoming week counts displayed correctly |
| F16 | Overflow "+N more" | Cell with >3 items shows expander |

---

## 11. Verification

After implementation, verify end-to-end:

1. `GET /api/itsm/change-calendar/?start_date=2026-07-01&end_date=2026-07-31&project_id=1` returns merged, sorted items
2. Calendar month grid renders with correct weekday headers (Mon-Sun), items in correct cells
3. Priority colors: P1=red, P2=orange, P3=blue, P4=gray, schedule=purple
4. Switch to week view → single row, 7 columns
5. Switch to timeline list → items grouped by date, chronological
6. Click ITSM item → popover shows ticket fields + "查看详情" link to `/apps/itsm/ticket/:id`
7. Click SchedulePlan item → popover shows schedule fields + link to schedule detail
8. Source filter: select "ITSM工单" only → only ticket items; select "定时计划" → only schedule items
9. Ticket type filter appears only when source is "全部" or "ITSM工单"
10. "今天" button snaps to current date in both month and week views
11. Month navigation arrows flip forward/backward correctly
12. Empty state: navigate to empty month → el-empty with "暂无变更"
13. Error state: simulate API failure → ElMessage.error with retry
14. Language switch: zh↔en → all labels, statuses, and popover text update
15. Project isolation: different project in switcher → different data
16. Hero stats update on tab switch and data load
