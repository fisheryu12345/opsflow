<template>
  <div class="schedule-day-list">
    <div v-if="items.length === 0" class="day-empty">{{ $t('message.slaSchedule.noDays') }}</div>
    <div v-for="(day, index) in items" :key="index" class="day-item">
      <div class="day-header">
        <div class="day-fields">
          <el-input v-model="day.name" :placeholder="$t('message.slaSchedule.dayName')" size="small" style="width:120px" />
          <el-input v-model="day.name_en" :placeholder="$t('message.slaSchedule.dayNameEn')" size="small" style="width:120px" />

          <!-- Weekday selector for NORMAL -->
          <template v-if="type === 'NORMAL'">
            <el-select v-model="dayOfWeekModels[index]" multiple size="small"
              :placeholder="$t('message.slaSchedule.dayOfWeek')"
              style="width:220px"
              @change="(vals: string[]) => onWeekdayChange(index, vals)">
              <el-option v-for="(label, key) in weekDayMap" :key="key" :label="label" :value="key" />
            </el-select>
          </template>

          <!-- Date range for WORKDAY/HOLIDAY -->
          <template v-if="type === 'WORKDAY' || type === 'HOLIDAY'">
            <el-date-picker v-model="day.start_date" type="date" size="small"
              :placeholder="$t('message.slaSchedule.startDate')" style="width:140px"
              value-format="YYYY-MM-DD" />
            <span class="date-sep">~</span>
            <el-date-picker v-model="day.end_date" type="date" size="small"
              :placeholder="$t('message.slaSchedule.endDate')" style="width:140px"
              value-format="YYYY-MM-DD" />
          </template>
        </div>
        <el-button size="small" type="danger" text @click="$emit('remove', index)">
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>

      <!-- Durations -->
      <div class="durations-section">
        <div class="durations-header">
          <span class="durations-label">{{ $t('message.slaSchedule.addDuration') }}</span>
          <el-button size="small" text type="primary" @click="addDuration(index)">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
        <div v-if="!day.durations || day.durations.length === 0" class="durations-empty">{{ $t('message.slaSchedule.noDurations') }}</div>
        <div v-for="(dur, di) in (day.durations || [])" :key="di" class="duration-row">
          <el-input v-model="dur.name" :placeholder="$t('message.slaSchedule.durationName')" size="small" style="width:100px" />
          <el-input v-model="dur.name_en" :placeholder="$t('message.slaSchedule.durationNameEn')" size="small" style="width:100px" />
          <el-time-picker v-model="dur.start_time" size="small"
            :placeholder="$t('message.slaSchedule.startTime')" style="width:130px"
            format="HH:mm" value-format="HH:mm:ss" />
          <span class="time-sep">-</span>
          <el-time-picker v-model="dur.end_time" size="small"
            :placeholder="$t('message.slaSchedule.endTime')" style="width:130px"
            format="HH:mm" value-format="HH:mm:ss" />
          <el-button size="small" type="danger" text @click="removeDuration(index, di)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <el-button size="small" style="margin-top:8px" @click="$emit('add')">
      <el-icon><Plus /></el-icon> {{ $t('message.slaSchedule.addDay') }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Plus, Delete } from '@element-plus/icons-vue'

const props = defineProps<{
  type: string
  items: any[]
  weekDayMap?: Record<string, string>
}>()

defineEmits<{
  'add': []
  'remove': [index: number]
  'update:item': [index: number, value: any]
}>()

// Track weekday selections per item for binding
const dayOfWeekModels = ref<string[][]>([])

watch(() => props.items, (newItems) => {
  dayOfWeekModels.value = (newItems || []).map((d: any) => {
    if (d.day_of_week && d.day_of_week !== '-1') {
      return d.day_of_week.split(',').filter(Boolean)
    }
    return []
  })
}, { immediate: true, deep: true })

function onWeekdayChange(index: number, vals: string[]) {
  if (props.items[index]) {
    props.items[index].day_of_week = vals.join(',') || '-1'
  }
}

function addDuration(dayIndex: number) {
  const day = props.items[dayIndex]
  if (!day.durations) day.durations = []
  day.durations.push({ name: '', name_en: '', start_time: '09:00:00', end_time: '18:00:00' })
}

function removeDuration(dayIndex: number, durIndex: number) {
  props.items[dayIndex].durations.splice(durIndex, 1)
}
</script>

<style lang="scss" scoped>
.schedule-day-list {
  min-height: 100px;
}
.day-empty {
  text-align: center; color: #909399; padding: 20px; font-size: 13px;
}
.day-item {
  border: 1px solid #ebeef5; border-radius: 8px; padding: 12px; margin-bottom: 10px;
}
.day-header {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.day-fields {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap; flex: 1;
}
.date-sep, .time-sep {
  color: #909399; font-size: 13px;
}
.durations-section {
  margin-top: 10px; border-top: 1px dashed #dcdfe6; padding-top: 8px;
}
.durations-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
}
.durations-label {
  font-size: 12px; color: #909399;
}
.durations-empty {
  font-size: 12px; color: #c0c4cc; padding: 4px 0;
}
.duration-row {
  display: flex; align-items: center; gap: 6px; margin-bottom: 6px; flex-wrap: wrap;
}
</style>
