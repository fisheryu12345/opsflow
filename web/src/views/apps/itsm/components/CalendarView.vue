<template>
  <div class="cv-root" v-loading="loading">
    <!-- View toggle (outside el-calendar header) -->
    <div class="cv-toggle">
      <el-radio-group v-model="viewMode" size="small">
        <el-radio-button value="month">
          {{ $t('message.changeCalendar.monthView') }}
        </el-radio-button>
        <el-radio-button value="week">
          {{ $t('message.changeCalendar.weekView') }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <el-calendar v-model="calendarDate" :class="{ 'cv-week-mode': viewMode === 'week' }">
      <template #date-cell="{ data }">
        <div
          class="cv-cell"
          :class="{
            'cv-today': isToday(data.date),
            'cv-other-month': data.type !== 'current-month',
          }"
          @click="onCellClick(data.date)"
        >
          <span class="cv-day-num">{{ data.date.getDate() }}</span>
          <div class="cv-items">
            <div
              v-for="item in getDayItems(data.date).slice(0, maxVisible)"
              :key="item.id"
              class="cv-item"
              :class="`cv-${item.priority?.toLowerCase() || 'schedule'}`"
              @click.stop="openPopover(item, $event)"
            >
              {{ item.title }}
            </div>
            <div
              v-if="getDayItems(data.date).length > maxVisible"
              class="cv-more"
            >
              +{{ getDayItems(data.date).length - maxVisible }}
              {{ $t('message.changeCalendar.moreItems') }}
            </div>
          </div>
        </div>
      </template>
    </el-calendar>

    <el-empty
      v-if="!loading && items.length === 0"
      :description="$t('message.changeCalendar.noItems')"
    />

    <ChangeDetailPopover
      v-if="selectedItem"
      :item="selectedItem"
      :visible="popoverVisible"
      :trigger-el="triggerEl"
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
import { useProjectStore } from '/@/stores/project'

const { t } = useI18n()
const projectStore = useProjectStore()
const hero = useHeroConsumer()

const props = defineProps<{
  active: boolean
  source?: string
  ticketType?: string
}>()

const maxVisible = 3
const viewMode = ref<'month' | 'week'>('month')
const calendarDate = ref(new Date())
const items = ref<CalendarItem[]>([])
const loading = ref(false)
const selectedItem = ref<CalendarItem | null>(null)
const popoverVisible = ref(false)
const triggerEl = ref<HTMLElement | null>(null)

const currentYear = computed(() => calendarDate.value.getFullYear())
const currentMonth = computed(() => calendarDate.value.getMonth())

function isToday(date: Date): boolean {
  const now = new Date()
  return date.toDateString() === now.toDateString()
}

// Build a map: "YYYY-MM-DD" → CalendarItem[] for O(1) lookup per cell
const itemMap = computed(() => {
  const map: Record<string, CalendarItem[]> = {}
  for (const item of items.value) {
    if (!item.start_time) continue
    const start = new Date(item.start_time)
    const end = item.end_time ? new Date(item.end_time) : start
    const cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate())
    const endDay = new Date(end.getFullYear(), end.getMonth(), end.getDate())
    while (cursor <= endDay) {
      const key = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}-${String(cursor.getDate()).padStart(2, '0')}`
      if (!map[key]) map[key] = []
      map[key].push(item)
      cursor.setDate(cursor.getDate() + 1)
    }
  }
  return map
})

function getDayItems(date: Date): CalendarItem[] {
  const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  return itemMap.value[key] || []
}

function openPopover(item: CalendarItem, event: Event) {
  selectedItem.value = item
  triggerEl.value = event.currentTarget as HTMLElement
  popoverVisible.value = true
}

function onCellClick(date: Date) {
  // Select the date (v-model updates automatically via el-calendar)
}

function upcomingCount(): number {
  const now = new Date()
  const weekEnd = new Date(now.getTime() + 7 * 86400000)
  return items.value.filter(it => {
    const start = new Date(it.start_time)
    return start >= now && start <= weekEnd
  }).length
}

async function fetchData() {
  loading.value = true
  try {
    const start = new Date(currentYear.value, currentMonth.value, 1)
    const end = new Date(currentYear.value, currentMonth.value + 1, 0)
    const res = await getChangeCalendar({
      start_date: start.toISOString().slice(0, 10),
      end_date: end.toISOString().slice(0, 10),
      project_id: projectStore.currentProjectId,
      source: props.source || undefined,
      ticket_type: props.ticketType || undefined,
    })
    items.value = res.data.items
    hero.reportStats([
      { label: t('message.changeCalendar.totalChanges'), value: res.data.total },
      { label: t('message.changeCalendar.upcomingWeek'), value: upcomingCount() },
    ])
  } catch {
    // Error handled by axios interceptor
  } finally {
    loading.value = false
  }
}

// Fetch when viewed month changes (via el-calendar v-model) or filters change
watch([currentYear, currentMonth], () => { fetchData() })
watch(() => props.active, (val) => { if (val && items.value.length === 0) fetchData() })
watch(() => props.source, () => { fetchData() })
watch(() => props.ticketType, () => { fetchData() })
onMounted(() => { if (props.active) fetchData() })
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;

.cv-root {
  width: 100%;
}

.cv-toggle {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}

// Week mode: hide all but the current week via CSS
.cv-week-mode :deep(.el-calendar-table) {
  .el-calendar-day {
    display: none;
    // Show only row containing today
    &:has(.cv-today) { display: table-cell; }
  }
  // Show the full row containing today
  tr:has(.cv-today) .el-calendar-day {
    display: table-cell;
  }
}

.cv-cell {
  min-height: 72px;
  padding: 2px 4px;
  cursor: pointer;
  position: relative;
}

.cv-today {
  background: #ecf5ff;
  border-radius: 4px;
}

.cv-other-month {
  opacity: 0.35;
}

.cv-day-num {
  font-size: 12px;
  color: #909399;
  position: absolute;
  top: 2px;
  right: 4px;
}

.cv-items {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.cv-item {
  font-size: 11px;
  padding: 1px 3px;
  border-radius: 2px;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-left: 3px solid transparent;
  &:hover { opacity: 0.8; }
}

.cv-p1 { border-left-color: #F56C6C; background: #fef0f0; }
.cv-p2 { border-left-color: #E6A23C; background: #fdf6ec; }
.cv-p3 { border-left-color: #409EFF; background: #ecf5ff; }
.cv-p4 { border-left-color: #909399; background: #f4f4f5; }
.cv-schedule { border-left-color: #A855F7; background: #f5f0ff; }

.cv-more {
  font-size: 11px;
  color: #409EFF;
  cursor: pointer;
  padding: 1px 3px;
}
</style>
