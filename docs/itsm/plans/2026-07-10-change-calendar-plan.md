# Implementation Plan: Change Calendar — 变更日历

> **Design Spec:** [docs/superpowers/specs/2026-07-10-change-calendar-design.md](../superpowers/specs/2026-07-10-change-calendar-design.md)
> **Priority:** P2
> **Date:** 2026-07-10

## Context

Add a change calendar page under ITSM that aggregates ITSM tickets and OpsFlow schedule plans into a unified calendar/timeline view. Backend: new aggregation API endpoint. Frontend: new page with month/week grid + timeline list, popover detail cards.

---

## Tasks

### 1. [Backend] Create Calendar Item Serializer

**File:** `backend/itsm/serializers/change_calendar.py` (NEW)

Follow the `CustomModelSerializer` pattern. This serializer is for output only — no model backing it, so use a plain `Serializer`.

```python
from rest_framework import serializers

class CalendarItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    source = serializers.CharField()
    title = serializers.CharField()
    ticket_sn = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField()
    status_display = serializers.CharField()
    priority = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    link = serializers.CharField()
    assignee = serializers.ListField(required=False)
    service_item_name = serializers.CharField(required=False, allow_blank=True)
    sla_deadline = serializers.DateTimeField(required=False, allow_null=True)
    cron_description = serializers.CharField(required=False, allow_blank=True)
```

**Why:** Unified response format for both ITSM tickets and SchedulePlan items. `required=False` fields render conditionally based on `source`.

**Verification:** Import succeeds; serializer validates the sample data from spec §2.3.

---

### 2. [Backend] Create Aggregation Service

**File:** `backend/itsm/services/change_calendar.py` (NEW)

Follow the service pattern: file-level `logger`, `@staticmethod` methods, lazy imports inside methods.

```python
import logging
from datetime import datetime, timedelta
from django.db.models import Q

logger = logging.getLogger(__name__)

class ChangeCalendarService:

    @staticmethod
    def aggregate(start_date, end_date, project_id, source=None, ticket_type=None):
        items = []

        if source is None or source == 'itsm_ticket':
            items.extend(ChangeCalendarService._get_ticket_items(
                start_date, end_date, project_id, ticket_type
            ))

        if source is None or source == 'opsflow_schedule':
            items.extend(ChangeCalendarService._get_schedule_items(
                start_date, end_date, project_id
            ))

        items.sort(key=lambda x: x['start_time'])
        return items

    @staticmethod
    def _get_ticket_items(start_date, end_date, project_id, ticket_type):
        from itsm.models import Ticket
        qs = Ticket.objects.filter(
            project_id=project_id,
            create_datetime__date__lte=end_date,
        ).exclude(current_status='draft')

        if ticket_type:
            qs = qs.filter(itsm_type=ticket_type)

        items = []
        for ticket in qs.select_related('workflow_version__workflow'):
            sla_deadline = ChangeCalendarService._get_sla_deadline(ticket)
            end_time = (
                ticket.finished_at.isoformat() if hasattr(ticket, 'finished_at') and ticket.finished_at
                else sla_deadline
            )
            items.append({
                'id': f'ticket_{ticket.id}',
                'source': 'itsm_ticket',
                'title': ticket.title,
                'ticket_sn': ticket.sn,
                'status': ticket.current_status,
                'status_display': dict(Ticket.STATUS_CHOICES).get(ticket.current_status, ''),
                'priority': ticket.priority,
                'start_time': ticket.create_datetime.isoformat(),
                'end_time': end_time,
                'link': f'/apps/itsm/ticket/{ticket.id}',
                'assignee': ticket.meta.get('assignee', []) if ticket.meta else [],
                'service_item_name': '',
                'sla_deadline': sla_deadline,
            })
        return items

    @staticmethod
    def _get_schedule_items(start_date, end_date, project_id):
        from opsflow.models import SchedulePlan
        qs = SchedulePlan.objects.filter(
            project_id=project_id,
            status__in=['active', 'paused'],
        )

        items = []
        for sp in qs:
            event_time = sp.scheduled_at or sp.next_run_at
            if event_time is None:
                continue
            event_date = event_time.date() if hasattr(event_time, 'date') else event_time
            if event_date < start_date or event_date > end_date:
                continue

            end_time = event_time + timedelta(hours=1)  # estimated 1hr execution

            items.append({
                'id': f'schedule_{sp.id}',
                'source': 'opsflow_schedule',
                'title': sp.name,
                'status': sp.status,
                'status_display': dict(SchedulePlan.Status.choices).get(sp.status, ''),
                'priority': None,
                'start_time': event_time.isoformat() if hasattr(event_time, 'isoformat') else str(event_time),
                'end_time': end_time.isoformat() if hasattr(end_time, 'isoformat') else str(end_time),
                'link': f'/apps/opsflow-template/schedule/{sp.id}',
                'cron_description': sp.cron_description or '',
            })
        return items

    @staticmethod
    def _get_sla_deadline(ticket):
        try:
            from itsm.models import SlaTask
            sla_task = SlaTask.objects.filter(ticket=ticket).first()
            if sla_task and sla_task.deadline:
                return sla_task.deadline.isoformat()
        except Exception:
            pass
        return None
```

**Why:** Cross-app aggregation logic belongs in the service layer per project architecture rules. Lazy imports avoid circular dependency issues. The `itsm_type` filter only applies to tickets.

**Verification:** Run `python manage.py shell -c "from itsm.services.change_calendar import ChangeCalendarService; print(ChangeCalendarService.aggregate(...))"` with real date/project values.

---

### 3. [Backend] Create View

**File:** `backend/itsm/views/change_calendar.py` (NEW)

Extend `ItsmProjectViewSet` but override `list` for the custom aggregation endpoint. This is not a standard CRUD ViewSet — it only has `list`.

```python
from rest_framework.decorators import action
from common.utils.json_response import DetailResponse
from itsm.views.workflow_views import ItsmProjectViewSet
from itsm.services.change_calendar import ChangeCalendarService
from itsm.serializers.change_calendar import CalendarItemSerializer


class ChangeCalendarViewSet(ItsmProjectViewSet):
    """变更日历 — aggregates ITSM tickets + OpsFlow schedules into a unified timeline."""
    model = None  # no single model — aggregation endpoint
    serializer_class = CalendarItemSerializer

    def list(self, request, *args, **kwargs):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        project_id = request.query_params.get('project_id')
        source = request.query_params.get('source', '')
        ticket_type = request.query_params.get('ticket_type', '')

        from datetime import date as date_type
        if not start_date or not end_date:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'start_date and end_date are required'})

        start_date = date_type.fromisoformat(start_date)
        end_date = date_type.fromisoformat(end_date)

        items = ChangeCalendarService.aggregate(
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            source=source or None,
            ticket_type=ticket_type or None,
        )

        serializer = self.get_serializer(items, many=True)
        return DetailResponse(data={
            'items': serializer.data,
            'total': len(items),
        })
```

**Why:** `ItsmProjectViewSet` provides auth (`IsAuthenticated`, `TenantPermission`) and dvadmin response conventions. Since there's no single model queryset, we override `list` for custom aggregation. Project filtering happens inside `ChangeCalendarService` via the `project_id` parameter.

**Verification:** `python manage.py test itsm.tests.test_change_calendar` (test file created in Task 4)

---

### 4. [Backend] Register URL

**File:** `backend/itsm/urls.py` (EDIT)

Add one line to the router registrations, before `urlpatterns`:

```python
router.register(r'change-calendar', ChangeCalendarViewSet, basename='change-calendar')
```

Import at top of file:
```python
from itsm.views.change_calendar import ChangeCalendarViewSet
```

**Why:** All ITSM ViewSets use `SimpleRouter` with kebab-case prefixes. The `basename` is needed because `ChangeCalendarViewSet` has no `queryset` (DRF requires it for URL name generation).

**Verification:** `python manage.py show_urls | grep change-calendar` shows the endpoint.

---

### 5. [Frontend] Add API Client

**File:** `web/src/api/itsm/index.ts` (EDIT)

Add the API function following existing patterns:

```typescript
export interface CalendarQuery {
  start_date: string
  end_date: string
  project_id: number
  source?: string
  ticket_type?: string
}

export interface CalendarItem {
  id: string
  source: 'itsm_ticket' | 'opsflow_schedule'
  title: string
  ticket_sn?: string
  status: string
  status_display: string
  priority?: string | null
  start_time: string
  end_time?: string | null
  link: string
  assignee?: string[]
  service_item_name?: string
  sla_deadline?: string | null
  cron_description?: string
}

export function getChangeCalendar(params: CalendarQuery) {
  return request<{ items: CalendarItem[]; total: number }>({
    url: '/api/itsm/change-calendar/',
    method: 'get',
    params,
  })
}
```

**Why:** Follows exact type export + function pattern from existing `web/src/api/itsm/index.ts`. `request` is the pre-configured axios instance from `web/src/utils/service.ts`. P0 note: i18n keys must been defined.

**Verification:** Import in a temp component; no TypeScript errors.

---

### 6. [Frontend] Add i18n Keys

**Files:** `web/src/i18n/pages/itsm/zh-cn.ts` and `web/src/i18n/pages/itsm/en.ts` (EDIT)

Add to the exported object in both files, under a `changeCalendar` namespace:

```typescript
// zh-cn.ts
changeCalendar: {
  title: '变更日历',
  monthView: '月视图',
  weekView: '周视图',
  listView: '列表',
  today: '今天',
  sourceAll: '全部',
  sourceTicket: 'ITSM工单',
  sourceSchedule: '定时计划',
  ticketType: '工单类型',
  ticketTypeChange: '变更申请',
  ticketTypeIncident: '事件工单',
  ticketTypeRequest: '服务请求',
  ticketTypeProblem: '问题管理',
  viewDetail: '查看详情',
  noItems: '暂无变更',
  loadError: '加载失败，请重试',
  retry: '重试',
  totalChanges: '变更总数',
  upcomingWeek: '本周待执行',
  slaDeadline: 'SLA截止',
  cronDesc: '执行频率',
  status: '状态',
  priority: '优先级',
  assignee: '处理人',
  serviceItem: '服务项',
  moreItems: '更多',
},

// en.ts
changeCalendar: {
  title: 'Change Calendar',
  monthView: 'Month',
  weekView: 'Week',
  listView: 'List',
  today: 'Today',
  sourceAll: 'All',
  sourceTicket: 'ITSM Ticket',
  sourceSchedule: 'Schedule',
  ticketType: 'Ticket Type',
  ticketTypeChange: 'Change',
  ticketTypeIncident: 'Incident',
  ticketTypeRequest: 'Request',
  ticketTypeProblem: 'Problem',
  viewDetail: 'View Details',
  noItems: 'No changes',
  loadError: 'Load failed, please retry',
  retry: 'Retry',
  totalChanges: 'Total Changes',
  upcomingWeek: 'Upcoming This Week',
  slaDeadline: 'SLA Deadline',
  cronDesc: 'Frequency',
  status: 'Status',
  priority: 'Priority',
  assignee: 'Assignee',
  serviceItem: 'Service Item',
  moreItems: 'more',
},
```

**Why:** i18n-first development is mandatory. All UI text must use `$t('message.itsmPage.changeCalendar.xxx')`.

**Verification:** Build frontend; switch zh↔en in app; verify keys exist without errors.

---

### 7. [Frontend] Create ChangeDetailPopover Component

**File:** `web/src/views/apps/itsm/components/ChangeDetailPopover.vue` (NEW)

Reusable popover component triggered on calendar item click. Uses `el-popover`.

```vue
<template>
  <el-popover
    :visible="visible"
    placement="right"
    :width="320"
    trigger="click"
    @hide="$emit('close')"
  >
    <template #reference>
      <slot />
    </template>
    <div class="cdp-card">
      <div class="cdp-header">
        <span class="cdp-title">{{ item.title }}</span>
        <span v-if="item.priority" class="cdp-priority" :class="priorityClass">
          {{ item.priority }}
        </span>
        <span v-else class="cdp-priority cdp-schedule">
          {{ $t('message.itsmPage.changeCalendar.sourceSchedule') }}
        </span>
      </div>
      <div class="cdp-divider" />
      <!-- ITSM fields -->
      <template v-if="item.source === 'itsm_ticket'">
        <div class="cdp-row"><span class="cdp-label">📋</span> {{ item.ticket_sn }}</div>
        <div class="cdp-row"><span class="cdp-label">📂</span> {{ item.service_item_name }}</div>
        <div class="cdp-row"><span class="cdp-label">⏰</span> {{ formatTimeRange(item) }}</div>
        <div class="cdp-row"><span class="cdp-label">📊</span> {{ item.status_display }}</div>
        <div class="cdp-row"><span class="cdp-label">👤</span> {{ item.assignee?.join(', ') }}</div>
        <div v-if="item.sla_deadline" class="cdp-row">
          <span class="cdp-label">⏳</span> {{ item.sla_deadline }}
        </div>
      </template>
      <!-- Schedule fields -->
      <template v-else>
        <div class="cdp-row"><span class="cdp-label">⏰</span> {{ formatTimeRange(item) }}</div>
        <div class="cdp-row"><span class="cdp-label">📊</span> {{ item.status_display }}</div>
        <div class="cdp-row"><span class="cdp-label">🔄</span> {{ item.cron_description }}</div>
      </template>
      <div class="cdp-divider" />
      <router-link :to="item.link" class="cdp-link">
        {{ $t('message.itsmPage.changeCalendar.viewDetail') }} →
      </router-link>
    </div>
  </el-popover>
</template>

<script setup lang="ts" name="ChangeDetailPopover">
import { computed } from 'vue'
import type { CalendarItem } from '/@/api/itsm'

const props = defineProps<{
  item: CalendarItem
  visible: boolean
}>()
defineEmits<{ close: [] }>()

const priorityClass = computed(() => ({
  'cdp-p1': props.item.priority === 'P1',
  'cdp-p2': props.item.priority === 'P2',
  'cdp-p3': props.item.priority === 'P3',
  'cdp-p4': props.item.priority === 'P4',
}))

function formatTimeRange(item: CalendarItem): string {
  if (!item.start_time) return ''
  const start = new Date(item.start_time).toLocaleString()
  if (!item.end_time) return start
  const end = new Date(item.end_time).toLocaleString()
  return `${start} ~ ${end}`
}
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;
.cdp-card { padding: 4px 0; }
.cdp-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.cdp-title { font-weight: 600; font-size: 14px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cdp-priority { font-size: 12px; padding: 1px 6px; border-radius: 4px; color: #fff; }
.cdp-p1 { background: #F56C6C; }
.cdp-p2 { background: #E6A23C; }
.cdp-p3 { background: #409EFF; }
.cdp-p4 { background: #909399; }
.cdp-schedule { background: #A855F7; }
.cdp-divider { height: 1px; background: #ebeef5; margin: 8px 0; }
.cdp-row { font-size: 13px; line-height: 1.8; display: flex; gap: 6px; }
.cdp-label { flex-shrink: 0; }
.cdp-link { display: block; text-align: center; color: #409EFF; margin-top: 4px; font-size: 13px; text-decoration: none; }
</style>
```

**Why:** Conditionally renders ITSM vs SchedulePlan fields based on `item.source`. Uses `el-popover` with `trigger="click"`. Separate component = reusable across both calendar and timeline views.

**Verification:** Import in CalendarView; click an item; popover renders correct fields per source type.

---

### 8. [Frontend] Create CalendarView Component

**File:** `web/src/views/apps/itsm/components/CalendarView.vue` (NEW)

Month/week calendar grid using `el-table` + `span-method`. Reference: `DutyCalendar.vue`.

```vue
<template>
  <div class="cv-root">
    <!-- Navigation bar -->
    <div class="cv-nav">
      <el-button-group>
        <el-button size="small" @click="prevMonth">←</el-button>
        <el-button size="small" @click="goToday">
          {{ $t('message.itsmPage.changeCalendar.today') }}
        </el-button>
        <el-button size="small" @click="nextMonth">→</el-button>
      </el-button-group>
      <span class="cv-nav-title">{{ currentYear }}年 {{ currentMonth + 1 }}月</span>
      <el-radio-group v-model="viewMode" size="small">
        <el-radio-button value="month">{{ $t('message.itsmPage.changeCalendar.monthView') }}</el-radio-button>
        <el-radio-button value="week">{{ $t('message.itsmPage.changeCalendar.weekView') }}</el-radio-button>
      </el-radio-group>
    </div>

    <!-- Calendar grid -->
    <el-table
      :data="calendarRows"
      :span-method="spanMethod"
      border
      class="cv-table"
      v-loading="loading"
    >
      <el-table-column
        v-for="(day, i) in dayHeaders"
        :key="i"
        :label="day"
        :width="columnWidth"
      >
        <template #default="{ row }">
          <div
            v-if="row[i]"
            class="cv-cell"
            :class="{ 'cv-today': row[i].isToday }"
          >
            <span class="cv-date">{{ row[i].day }}</span>
            <div class="cv-items">
              <div
                v-for="item in row[i].items.slice(0, maxVisible)"
                :key="item.id"
                class="cv-item"
                :class="`cv-${item.priority?.toLowerCase() || 'schedule'}`"
                @click.stop="openPopover(item, $event)"
              >
                {{ item.title }}
              </div>
              <div
                v-if="row[i].items.length > maxVisible"
                class="cv-more"
                @click="row[i].expanded = !row[i].expanded"
              >
                +{{ row[i].items.length - maxVisible }} {{ $t('message.itsmPage.changeCalendar.moreItems') }}
              </div>
            </div>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- Popover -->
    <ChangeDetailPopover
      v-if="selectedItem"
      :item="selectedItem"
      :visible="popoverVisible"
      @close="popoverVisible = false"
    />
  </div>
</template>

<script setup lang="ts" name="CalendarView">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { getChangeCalendar, type CalendarItem } from '/@/api/itsm'
import ChangeDetailPopover from './ChangeDetailPopover.vue'
import { useAppStore } from '/@/stores/app'

const { t } = useI18n()
const appStore = useAppStore()
const hero = useHeroConsumer()

const props = defineProps<{ active: boolean }>()

const dayHeaders = ['一', '二', '三', '四', '五', '六', '日']
const maxVisible = 3
const viewMode = ref<'month' | 'week'>('month')
const currentDate = ref(new Date())
const items = ref<CalendarItem[]>([])
const loading = ref(false)
const selectedItem = ref<CalendarItem | null>(null)
const popoverVisible = ref(false)

const currentYear = computed(() => currentDate.value.getFullYear())
const currentMonth = computed(() => currentDate.value.getMonth())
const columnWidth = computed(() => viewMode.value === 'week' ? undefined : undefined)

// Build calendar rows: [{0: {day, items, isToday}, 1: {...}, ...}]
const calendarRows = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month, 1)
  // Monday=0 (China locale): getDay() returns 0=Sun → adjust to 6=Sun, 0=Mon
  let startDow = firstDay.getDay() - 1
  if (startDow < 0) startDow = 6
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const today = new Date()
  const todayStr = today.toDateString()

  const rows: Record<number, any>[] = []
  let row: Record<number, any> = {}
  let col = startDow

  for (let d = 1; d <= daysInMonth; d++) {
    if (col >= 7) { rows.push(row); row = {}; col = 0 }
    const date = new Date(year, month, d)
    const dateStr = date.toDateString()
    const dayItems = items.value.filter(it => {
      const start = new Date(it.start_time)
      const end = it.end_time ? new Date(it.end_time) : start
      return date >= new Date(start.getFullYear(), start.getMonth(), start.getDate())
          && date <= new Date(end.getFullYear(), end.getMonth(), end.getDate())
    })
    row[col] = { day: d, items: dayItems, isToday: dateStr === todayStr, expanded: false }
    col++
  }
  if (Object.keys(row).length > 0) rows.push(row)

  if (viewMode.value === 'week') {
    // Find which row contains today
    const todayRow = rows.findIndex(r =>
      Object.values(r).some((v: any) => v?.isToday)
    )
    const idx = todayRow >= 0 ? todayRow : 0
    return [rows[idx]]
  }

  return rows
})

function prevMonth() {
  if (viewMode.value === 'month') {
    currentDate.value = new Date(currentYear.value, currentMonth.value - 1, 1)
  } else {
    currentDate.value = new Date(currentDate.value.getTime() - 7 * 86400000)
  }
}

function nextMonth() {
  if (viewMode.value === 'month') {
    currentDate.value = new Date(currentYear.value, currentMonth.value + 1, 1)
  } else {
    currentDate.value = new Date(currentDate.value.getTime() + 7 * 86400000)
  }
}

function goToday() {
  currentDate.value = new Date()
}

function spanMethod({ row, column }: any) {
  // Simplified: no cross-day spanning in P2; items render independently per cell
  return { rowspan: 1, colspan: 1 }
}

function openPopover(item: CalendarItem, event: Event) {
  selectedItem.value = item
  popoverVisible.value = true
}

async function fetchData() {
  loading.value = true
  try {
    const start = new Date(currentYear.value, currentMonth.value, 1)
    const end = new Date(currentYear.value, currentMonth.value + 1, 0)
    const res = await getChangeCalendar({
      start_date: start.toISOString().slice(0, 10),
      end_date: end.toISOString().slice(0, 10),
      project_id: appStore.currentProjectId,
    })
    items.value = res.data.items
    hero.reportStats([
      { label: t('message.itsmPage.changeCalendar.totalChanges'), value: res.data.total },
      { label: t('message.itsmPage.changeCalendar.upcomingWeek'), value: upcomingCount() },
    ])
  } catch {
    // Error handled by axios interceptor (ElMessage.error)
  } finally {
    loading.value = false
  }
}

function upcomingCount(): number {
  const now = new Date()
  const weekEnd = new Date(now.getTime() + 7 * 86400000)
  return items.value.filter(it => {
    const start = new Date(it.start_time)
    return start >= now && start <= weekEnd
  }).length
}

watch([currentYear, currentMonth, viewMode], () => { fetchData() })
watch(() => props.active, (val) => { if (val && items.value.length === 0) fetchData() })
onMounted(() => { if (props.active) fetchData() })
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;
.cv-root { width: 100%; }
.cv-nav { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.cv-nav-title { font-size: 16px; font-weight: 600; flex: 1; }
.cv-table { width: 100%; }
.cv-cell { min-height: 80px; padding: 4px; position: relative; }
.cv-cell.cv-today { background: #ecf5ff; }
.cv-date { font-size: 12px; color: #909399; position: absolute; top: 4px; right: 6px; }
.cv-items { margin-top: 20px; display: flex; flex-direction: column; gap: 2px; }
.cv-item { 
  font-size: 11px; padding: 1px 4px; border-radius: 3px; cursor: pointer;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  border-left: 3px solid transparent;
  &:hover { opacity: 0.8; }
}
.cv-p1 { border-left-color: #F56C6C; background: #fef0f0; }
.cv-p2 { border-left-color: #E6A23C; background: #fdf6ec; }
.cv-p3 { border-left-color: #409EFF; background: #ecf5ff; }
.cv-p4 { border-left-color: #909399; background: #f4f4f5; }
.cv-null, .cv-schedule { border-left-color: #A855F7; background: #f5f0ff; }
.cv-more { font-size: 11px; color: #409EFF; cursor: pointer; padding: 1px 4px; }
</style>
```

**Why:** Uses `el-table` + manual row/col computation to build the calendar grid (same approach as `DutyCalendar.vue`). Monday-first week start. Priority colors via CSS classes. `useHeroConsumer().reportStats()` for hero stats.

**Verification:** Navigate to /apps/itsm/change-calendar; month grid renders with items in correct cells; "today" cell highlighted; week view shows single row.

---

### 9. [Frontend] Create TimelineView Component

**File:** `web/src/views/apps/itsm/components/TimelineView.vue` (NEW)

Grouped timeline list with custom vertical timeline CSS. Reference: `TicketDetail.vue`.

```vue
<template>
  <div class="tv-root" v-loading="loading">
    <el-empty
      v-if="!loading && groupedItems.length === 0"
      :description="$t('message.itsmPage.changeCalendar.noItems')"
    />

    <div v-for="group in groupedItems" :key="group.date" class="tv-group">
      <div class="tv-date-header">{{ group.dateLabel }}</div>
      <div class="tv-items">
        <div v-for="item in group.items" :key="item.id" class="tv-item" @click="openPopover(item)">
          <div class="tv-dot" :class="`tv-${item.priority?.toLowerCase() || 'schedule'}`" />
          <div class="tv-content">
            <div class="tv-time">{{ formatTime(item) }}</div>
            <div class="tv-main">
              <span class="tv-title">{{ item.title }}</span>
              <span v-if="item.priority" class="tv-badge" :class="`tv-badge-${item.priority.toLowerCase()}`">
                {{ item.priority }}
              </span>
              <span class="tv-status">{{ item.status_display }}</span>
              <span v-if="item.assignee?.length" class="tv-assignee">{{ item.assignee.join(', ') }}</span>
            </div>
            <div class="tv-sub">
              <template v-if="item.source === 'itsm_ticket'">
                {{ item.ticket_sn }}  {{ item.service_item_name }}
              </template>
              <template v-else>
                {{ item.cron_description }}
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <ChangeDetailPopover
      v-if="selectedItem"
      :item="selectedItem"
      :visible="popoverVisible"
      @close="popoverVisible = false"
    />
  </div>
</template>

<script setup lang="ts" name="TimelineView">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { getChangeCalendar, type CalendarItem } from '/@/api/itsm'
import ChangeDetailPopover from './ChangeDetailPopover.vue'
import { useAppStore } from '/@/stores/app'

const { t } = useI18n()
const appStore = useAppStore()
const hero = useHeroConsumer()
const props = defineProps<{ active: boolean }>()

const currentDate = ref(new Date())
const items = ref<CalendarItem[]>([])
const loading = ref(false)
const selectedItem = ref<CalendarItem | null>(null)
const popoverVisible = ref(false)

const groupedItems = computed(() => {
  const groups: Record<string, { date: string; dateLabel: string; items: CalendarItem[] }> = {}
  const sorted = [...items.value].sort((a, b) =>
    new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
  )
  for (const item of sorted) {
    const d = new Date(item.start_time)
    const key = d.toDateString()
    if (!groups[key]) {
      groups[key] = {
        date: key,
        dateLabel: `${d.getMonth() + 1}月${d.getDate()}日  ${['日','一','二','三','四','五','六'][d.getDay()]}`,
        items: [],
      }
    }
    groups[key].items.push(item)
  }
  return Object.values(groups)
})

function formatTime(item: CalendarItem): string {
  if (!item.start_time) return ''
  const start = new Date(item.start_time)
  const s = `${String(start.getHours()).padStart(2,'0')}:${String(start.getMinutes()).padStart(2,'0')}`
  if (!item.end_time) return s
  const end = new Date(item.end_time)
  const e = `${String(end.getHours()).padStart(2,'0')}:${String(end.getMinutes()).padStart(2,'0')}`
  return `${s} ───── ${e}`
}

function openPopover(item: CalendarItem) {
  selectedItem.value = item
  popoverVisible.value = true
}

async function fetchData() {
  loading.value = true
  try {
    const year = currentDate.value.getFullYear()
    const month = currentDate.value.getMonth()
    const start = new Date(year, month, 1)
    const end = new Date(year, month + 1, 0)
    const res = await getChangeCalendar({
      start_date: start.toISOString().slice(0, 10),
      end_date: end.toISOString().slice(0, 10),
      project_id: appStore.currentProjectId,
    })
    items.value = res.data.items
    hero.reportStats([
      { label: t('message.itsmPage.changeCalendar.totalChanges'), value: res.data.total },
    ])
  } catch {
    // Error handled by axios interceptor
  } finally {
    loading.value = false
  }
}

watch(() => props.active, (val) => { if (val && items.value.length === 0) fetchData() })
onMounted(() => { if (props.active) fetchData() })
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;
.tv-root { width: 100%; }
.tv-group { margin-bottom: 16px; }
.tv-date-header { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 8px; padding-left: 24px; }
.tv-items { position: relative; padding-left: 16px; border-left: 2px solid #e4e7ed; margin-left: 8px; }
.tv-item { display: flex; gap: 10px; padding: 8px 0; cursor: pointer; position: relative; &:hover { background: #f5f7fa; } }
.tv-dot {
  width: 10px; height: 10px; border-radius: 50%; margin-top: 4px; flex-shrink: 0;
  position: absolute; left: -22px; border: 2px solid #fff;
}
.tv-p1 { background: #F56C6C; }
.tv-p2 { background: #E6A23C; }
.tv-p3 { background: #409EFF; }
.tv-p4 { background: #909399; }
.tv-schedule { background: #A855F7; }
.tv-content { flex: 1; min-width: 0; }
.tv-time { font-size: 12px; color: #909399; margin-bottom: 2px; }
.tv-main { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tv-title { font-size: 13px; font-weight: 500; }
.tv-badge { font-size: 11px; padding: 0 4px; border-radius: 3px; color: #fff; }
.tv-badge-p1 { background: #F56C6C; }
.tv-badge-p2 { background: #E6A23C; }
.tv-badge-p3 { background: #409EFF; }
.tv-badge-p4 { background: #909399; }
.tv-status { font-size: 12px; color: #909399; }
.tv-assignee { font-size: 12px; color: #606266; }
.tv-sub { font-size: 12px; color: #909399; margin-top: 2px; }
</style>
```

**Why:** Grouped by date with vertical timeline line + colored dots (same visual pattern as `TicketDetail.vue` approval timeline). Uses `useHeroConsumer().reportStats()` for hero.

**Verification:** Navigate to timeline tab; items grouped by date; dot colors match priority mapping; click opens popover.

---

### 10. [Frontend] Create ChangeCalendar Component (ITSM Sub-Tab)

**File:** `web/src/views/apps/itsm/ChangeCalendar.vue` (NEW)

This is a **sub-tab** inside `index.vue`'s ITSM page. The ITSM page provides the hero, so ChangeCalendar only needs filters + its own calendar/timeline content. It uses `useHeroConsumer().reportStats()` to update the ITSM hero stats dynamically.

```vue
<template>
  <div class="cc-root">
    <!-- Source + Ticket Type filters (calendar-specific, above ITSM hero) -->
    <div class="cc-filters">
      <el-select
        v-model="source"
        :placeholder="$t('message.itsmPage.changeCalendar.sourceAll')"
        size="default"
        @change="onFilterChange"
      >
        <el-option :label="$t('message.itsmPage.changeCalendar.sourceAll')" value="" />
        <el-option :label="$t('message.itsmPage.changeCalendar.sourceTicket')" value="itsm_ticket" />
        <el-option :label="$t('message.itsmPage.changeCalendar.sourceSchedule')" value="opsflow_schedule" />
      </el-select>
      <el-select
        v-if="source !== 'opsflow_schedule'"
        v-model="ticketType"
        :placeholder="$t('message.itsmPage.changeCalendar.ticketType')"
        size="default"
        @change="onFilterChange"
      >
        <el-option :label="$t('message.itsmPage.changeCalendar.ticketTypeChange')" value="change" />
        <el-option :label="$t('message.itsmPage.changeCalendar.ticketTypeIncident')" value="incident" />
        <el-option :label="$t('message.itsmPage.changeCalendar.ticketTypeRequest')" value="request" />
        <el-option :label="$t('message.itsmPage.changeCalendar.ticketTypeProblem')" value="problem" />
      </el-select>
    </div>

    <!-- Sub-tabs: Calendar | Timeline -->
    <el-tabs v-model="subTab" class="cc-tabs">
      <el-tab-pane name="month" :label="$t('message.itsmPage.changeCalendar.monthView')" />
      <el-tab-pane name="timeline" :label="$t('message.itsmPage.changeCalendar.listView')" />
    </el-tabs>

    <!-- Sub-tab content (lazy-load) -->
    <div v-if="isVisited('month')" v-show="subTab === 'month'" class="cc-section">
      <CalendarView
        :active="active && subTab === 'month'"
        :source="source"
        :ticket-type="ticketType"
      />
    </div>
    <div v-if="isVisited('timeline')" v-show="subTab === 'timeline'" class="cc-section">
      <TimelineView
        :active="active && subTab === 'timeline'"
        :source="source"
        :ticket-type="ticketType"
      />
    </div>
  </div>
</template>

<script setup lang="ts" name="ChangeCalendar">
import { ref } from 'vue'
import { useTabLazyLoad } from '/@/composables/useTabLazyLoad'
import CalendarView from './components/CalendarView.vue'
import TimelineView from './components/TimelineView.vue'

defineProps<{ active: boolean }>()

const { activeTab: subTab, isVisited } = useTabLazyLoad('month')
const source = ref('')
const ticketType = ref('')

function onFilterChange() { /* child components watch source/ticketType */ }
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;
.cc-root { width: 100%; }
.cc-filters { display: flex; gap: 12px; margin-bottom: 12px; }
.cc-tabs { background: #fff; border-radius: 8px 8px 0 0; padding: 0 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.cc-section { padding: 20px; background: #fff; border-radius: 0 0 8px 8px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
</style>
```

**Why:** This is a sub-tab within the ITSM page — the ITSM `index.vue` already provides the hero. `ChangeCalendar` only manages its own filter bar and calendar/timeline sub-tabs. Filter values (`source`, `ticketType`) are passed as props to child views.

**Verification:** Navigate to ITSM → 变更日历 tab; filter bar visible; month view and timeline sub-tabs switch correctly.

---

### 11. [Backend] Register Tab in Seed Data

**File:** `backend/iam/management/commands/seed_iam_page_configs.py` (EDIT)

Add a page tab entry for change-calendar under the ITSM app. The ITSM `index.vue` loads tabs from `/api/iam/page-permissions/?app=itsm`:

```python
# Find existing ITSM page config entry and add to its tabs list:
{
    'key': 'change-calendar',
    'label_zh': '变更日历',
    'label_en': 'Change Calendar',
    'icon': 'Calendar',
    'sort': 90,
}
```

The exact format depends on how the seed data structures page permissions. Check the existing ITSM entries (e.g., escalation: key=`escalation`, schedule: key=`schedule`) and follow the same pattern.

**Why:** ITSM uses backend-controlled routing. The `index.vue` fetches page permissions and renders tabs dynamically. Each tab key maps to a `v-if="isVisited('key')"` block in the template.

**Verification:** After seeding, `GET /api/iam/page-permissions/?app=itsm` returns `change-calendar` in the tabs array.

---

### 12. [Frontend] Register Tab in ITSM index.vue

**File:** `web/src/views/apps/itsm/index.vue` (EDIT)

Two changes needed:

**A. Add template block** (after the last tab section, before `</div>` closing `itsm-body`):

```html
<!-- TAB: Change Calendar -->
<div v-if="isVisited('change-calendar')" v-show="activeTab === 'change-calendar'" class="itsm-section g-fade-in-up">
  <ChangeCalendar :active="activeTab === 'change-calendar'" />
</div>
```

**B. Add import** in the script section (alongside other imports):

```typescript
import ChangeCalendar from './ChangeCalendar.vue'
```

**Why:** The ITSM `index.vue` uses explicit template blocks per tab key — no dynamic component map. The `isVisited('change-calendar')` gate enables lazy loading. The `active` prop tells ChangeCalendar when it's the visible tab.

**Verification:** Click "变更日历" tab in ITSM page → ChangeCalendar renders; switch away and back → lazy-load works.

---

## Verification

### Backend

- [ ] `python manage.py test itsm` — all existing tests still pass
- [ ] `curl "http://localhost:8000/api/itsm/change-calendar/?start_date=2026-07-01&end_date=2026-07-31&project_id=1"` — returns merged items
- [ ] API returns 400 when missing required params
- [ ] Different `project_id` returns disjoint item sets

### Frontend

- [ ] `npx vue-tsc --noEmit` — no TypeScript errors
- [ ] Calendar month view renders with Monday-first columns
- [ ] "今天" button snaps to current date
- [ ] Week view shows single-row 7-column grid
- [ ] Timeline view groups by date, color dots match priority
- [ ] Popover on click shows correct fields per source type
- [ ] "查看详情" link navigates to correct detail page
- [ ] Source filter switches data correctly
- [ ] Empty state renders el-empty
- [ ] i18n: switch zh↔en, all labels update

### End-to-End

1. Navigate to ITSM → 变更日历
2. Month grid shows current month with items in correct days
3. Click item → popover with metadata
4. Click "查看详情" → navigates to ticket/schedule detail
5. Switch to "列表" tab → timeline groups by date
6. Filter by source "ITSM工单" → only ticket items
7. Switch to English → all labels update correctly
