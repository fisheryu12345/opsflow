<template>
  <div class="cc-root">
    <!-- Source + Ticket Type filters -->
    <div class="cc-filters">
      <el-select
        v-model="sourceFilter"
        :placeholder="$t('message.changeCalendar.sourceAll')"
        size="default"
        clearable
      >
        <el-option
          :label="$t('message.changeCalendar.sourceAll')"
          value=""
        />
        <el-option
          :label="$t('message.changeCalendar.sourceTicket')"
          value="itsm_ticket"
        />
        <el-option
          :label="$t('message.changeCalendar.sourceSchedule')"
          value="opsflow_schedule"
        />
      </el-select>
      <el-select
        v-if="sourceFilter !== 'opsflow_schedule'"
        v-model="typeFilter"
        :placeholder="$t('message.changeCalendar.ticketType')"
        size="default"
        clearable
      >
        <el-option
          :label="$t('message.changeCalendar.ticketTypeChange')"
          value="change"
        />
        <el-option
          :label="$t('message.changeCalendar.ticketTypeIncident')"
          value="incident"
        />
        <el-option
          :label="$t('message.changeCalendar.ticketTypeRequest')"
          value="request"
        />
        <el-option
          :label="$t('message.changeCalendar.ticketTypeProblem')"
          value="problem"
        />
      </el-select>
    </div>

    <!-- Sub-tabs: Month | Timeline -->
    <el-tabs v-model="subTab" class="cc-tabs">
      <el-tab-pane name="month">
        <template #label>
          <el-icon><Calendar /></el-icon>
          {{ tabLabels.month }}
        </template>
      </el-tab-pane>
      <el-tab-pane name="timeline">
        <template #label>
          <el-icon><List /></el-icon>
          {{ tabLabels.timeline }}
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- Sub-tab content (lazy-load) -->
    <div
      v-if="isVisited('month')"
      v-show="subTab === 'month'"
      class="cc-section"
    >
      <CalendarView
        :active="active && subTab === 'month'"
        :source="sourceFilter"
        :ticket-type="typeFilter"
      />
    </div>
    <div
      v-if="isVisited('timeline')"
      v-show="subTab === 'timeline'"
      class="cc-section"
    >
      <TimelineView
        :active="active && subTab === 'timeline'"
        :source="sourceFilter"
        :ticket-type="typeFilter"
      />
    </div>
  </div>
</template>

<script setup lang="ts" name="ChangeCalendar">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Calendar, List } from '@element-plus/icons-vue'
import { useTabLazyLoad } from '/@/composables/useTabLazyLoad'
import CalendarView from './components/CalendarView.vue'
import TimelineView from './components/TimelineView.vue'

defineProps<{ active: boolean }>()

const { t } = useI18n()
const subTab = ref('month')
const { isVisited } = useTabLazyLoad({
  tabs: ['month', 'timeline'],
  activeTab: subTab,
})
const sourceFilter = ref('')
const typeFilter = ref('')
const tabLabels = computed(() => ({
  month: t('message.changeCalendar.monthView'),
  timeline: t('message.changeCalendar.listView'),
}))
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;
.cc-root { width: 100%; }
.cc-filters { display: flex; gap: 12px; margin-bottom: 12px; }
.cc-tabs { background: #fff; border-radius: 8px 8px 0 0; padding: 0 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.cc-section { padding: 20px; background: #fff; border-radius: 0 0 8px 8px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
</style>
