<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="cdp-overlay"
      @click.self="emit('close')"
    >
      <div class="cdp-card" :style="cardStyle" @click.stop>
        <div class="cdp-header">
          <span class="cdp-title">{{ item.title }}</span>
          <span v-if="item.priority" class="cdp-priority" :class="priorityClass">
            {{ item.priority }}
          </span>
          <span v-else class="cdp-priority cdp-schedule">
            {{ $t('message.changeCalendar.sourceSchedule') }}
          </span>
        </div>
        <div class="cdp-divider" />
        <template v-if="item.source === 'itsm_ticket'">
          <div class="cdp-row"><span class="cdp-label">SN</span> {{ item.ticket_sn }}</div>
          <div v-if="item.service_item_name" class="cdp-row">
            <span class="cdp-label">SVC</span> {{ item.service_item_name }}
          </div>
          <div class="cdp-row"><span class="cdp-label">TIME</span> {{ formatTimeRange(item) }}</div>
          <div class="cdp-row">
            <span class="cdp-label">STAT</span>
            {{ $t('message.changeCalendar.status') }}: {{ item.status_display }}
          </div>
          <div v-if="item.assignee?.length" class="cdp-row">
            <span class="cdp-label">ASGN</span>
            {{ $t('message.changeCalendar.assignee') }}: {{ item.assignee.join(', ') }}
          </div>
          <div v-if="item.sla_deadline" class="cdp-row">
            <span class="cdp-label">SLA</span>
            {{ $t('message.changeCalendar.slaDeadline') }}: {{ item.sla_deadline }}
          </div>
        </template>
        <template v-else>
          <div class="cdp-row"><span class="cdp-label">TIME</span> {{ formatTimeRange(item) }}</div>
          <div class="cdp-row">
            <span class="cdp-label">STAT</span>
            {{ $t('message.changeCalendar.status') }}: {{ item.status_display }}
          </div>
          <div v-if="item.cron_description" class="cdp-row">
            <span class="cdp-label">FREQ</span>
            {{ $t('message.changeCalendar.cronDesc') }}: {{ item.cron_description }}
          </div>
        </template>
        <div class="cdp-divider" />
        <router-link :to="item.link" class="cdp-link" @click="emit('close')">
          {{ $t('message.changeCalendar.viewDetail') }}
        </router-link>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts" name="ChangeDetailPopover">
import { computed, onMounted, onBeforeUnmount } from 'vue'
import type { CalendarItem } from '/@/api/itsm'

const props = defineProps<{
  item: CalendarItem
  visible: boolean
  triggerEl: HTMLElement | null
}>()
const emit = defineEmits<{ close: [] }>()

const priorityClass = computed(() => ({
  'cdp-p1': props.item.priority === 'P1',
  'cdp-p2': props.item.priority === 'P2',
  'cdp-p3': props.item.priority === 'P3',
  'cdp-p4': props.item.priority === 'P4',
}))

const cardStyle = computed(() => {
  if (!props.triggerEl) return {}
  const r = props.triggerEl.getBoundingClientRect()
  const top = r.bottom + 4
  const left = Math.min(r.left, window.innerWidth - 340)
  return {
    position: 'fixed' as const,
    top: top + 'px',
    left: left + 'px',
    width: '320px',
    zIndex: 3000,
  }
})

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.visible) {
    emit('close')
  }
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

function formatTimeRange(item: CalendarItem): string {
  if (!item.start_time) return ''
  const start = new Date(item.start_time).toLocaleString()
  if (!item.end_time) return start
  const end = new Date(item.end_time).toLocaleString()
  return `${start} ~ ${end}`
}
</script>

<style scoped lang="scss">
.cdp-overlay {
  position: fixed; inset: 0; z-index: 2999;
}
.cdp-card {
  background: #fff; border-radius: 8px; padding: 12px 16px;
  box-shadow: 0 6px 24px rgba(0,0,0,.12);
}
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
.cdp-label { flex-shrink: 0; color: #909399; font-size: 11px; min-width: 32px; }
.cdp-link { display: block; text-align: center; color: #409EFF; margin-top: 4px; font-size: 13px; text-decoration: none; }
</style>
