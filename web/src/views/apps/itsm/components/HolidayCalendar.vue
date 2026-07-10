<template>
  <div class="holiday-calendar">
    <div class="date-range-row">
      <el-date-picker
        :model-value="startDate"
        @update:model-value="onStartChange"
        type="date"
        size="small"
        :placeholder="$t('message.slaSchedule.startDate')"
        value-format="YYYY-MM-DD"
        style="width:150px"
      />
      <span class="range-sep">~</span>
      <el-date-picker
        :model-value="endDate"
        @update:model-value="onEndChange"
        type="date"
        size="small"
        :placeholder="$t('message.slaSchedule.endDate')"
        value-format="YYYY-MM-DD"
        style="width:150px"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  startDate?: string | null
  endDate?: string | null
}>()

const emit = defineEmits<{
  'update:startDate': [value: string | null]
  'update:endDate': [value: string | null]
}>()

function onStartChange(val: string | null) {
  emit('update:startDate', val)
}
function onEndChange(val: string | null) {
  emit('update:endDate', val)
}
</script>

<style lang="scss" scoped>
.holiday-calendar { }
.date-range-row {
  display: flex; align-items: center; gap: 6px;
}
.range-sep {
  color: #909399; font-size: 13px;
}
</style>
