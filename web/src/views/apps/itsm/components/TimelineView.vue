<template>
  <div class="tv-root" v-loading="loading">
    <el-empty
      v-if="!loading && groupedItems.length === 0"
      :description="$t('message.changeCalendar.noItems')"
    />

    <div v-for="group in groupedItems" :key="group.date" class="tv-group">
      <div class="tv-date-header">{{ group.dateLabel }}</div>
      <div class="tv-items">
        <div
          v-for="item in group.items"
          :key="item.id"
          class="tv-item"
          @click="openPopover(item, $event)"
        >
          <div
            class="tv-dot"
            :class="`tv-${item.priority?.toLowerCase() || 'schedule'}`"
          />
          <div class="tv-content">
            <div class="tv-time">{{ formatTime(item) }}</div>
            <div class="tv-main">
              <span class="tv-title">{{ item.title }}</span>
              <span
                v-if="item.priority"
                class="tv-badge"
                :class="`tv-badge-${item.priority.toLowerCase()}`"
              >
                {{ item.priority }}
              </span>
              <span class="tv-status">{{ item.status_display }}</span>
              <span
                v-if="item.assignee?.length"
                class="tv-assignee"
              >
                {{ item.assignee.join(', ') }}
              </span>
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

    <div ref="popoverRef">
      <ChangeDetailPopover
        v-if="selectedItem"
        :item="selectedItem"
        :visible="popoverVisible"
        :trigger-el="triggerEl"
        @close="popoverVisible = false"
      />
    </div>
  </div>
</template>

<script setup lang="ts" name="TimelineView">
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

const currentDate = ref(new Date())
const items = ref<CalendarItem[]>([])
const loading = ref(false)
const selectedItem = ref<CalendarItem | null>(null)
const popoverVisible = ref(false)
const triggerEl = ref<HTMLElement | null>(null)
const popoverRef = ref<HTMLElement>()

const groupedItems = computed(() => {
  const groups: Record<string, { date: string; dateLabel: string; items: CalendarItem[] }> = {}
  const sorted = [...items.value].sort(
    (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
  )
  for (const item of sorted) {
    const d = new Date(item.start_time)
    const key = d.toDateString()
    if (!groups[key]) {
      groups[key] = {
        date: key,
        dateLabel: `${t('message.changeCalendar.monthDay', { month: d.getMonth() + 1, day: d.getDate() })}  ${dayNames.value[d.getDay()]}`,
        items: [],
      }
    }
    groups[key].items.push(item)
  }
  return Object.values(groups)
})

// Sunday-first day names from i18n (matches JS getDay() convention)
const dayNames = computed(() => t('message.changeCalendar.daysShort') as unknown as string[])

function formatTime(item: CalendarItem): string {
  if (!item.start_time) return ''
  const start = new Date(item.start_time)
  const s = `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')}`
  if (!item.end_time) return s
  const end = new Date(item.end_time)
  const e = `${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}`
  return `${s} ─── ${e}`
}

function openPopover(item: CalendarItem, event: Event) {
  selectedItem.value = item
  triggerEl.value = event.currentTarget as HTMLElement
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
      project_id: projectStore.currentProjectId,
      source: props.source || undefined,
      ticket_type: props.ticketType || undefined,
    })
    items.value = res.data.items
    hero.reportStats([
      { label: t('message.changeCalendar.totalChanges'), value: res.data.total },
    ])
  } catch {
    // Error handled by axios interceptor
  } finally {
    loading.value = false
  }
}

watch(() => props.active, (val) => { if (val && items.value.length === 0) fetchData() })
watch(() => props.source, () => { fetchData() })
watch(() => props.ticketType, () => { fetchData() })
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
