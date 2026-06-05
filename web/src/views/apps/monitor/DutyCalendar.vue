<template>
  <div class="duty-page">
    <div class="duty-header">
      <h2 class="duty-title">值班日历</h2>
      <div class="duty-controls">
        <el-button-group style="margin-right:12px;">
          <el-button size="small" @click="prevMonth">‹</el-button>
          <el-button size="small" disabled>{{ year }}年{{ month }}月</el-button>
          <el-button size="small" @click="nextMonth">›</el-button>
        </el-button-group>
        <el-select v-model="planId" placeholder="选择值班计划" size="small" style="width:200px;" @change="loadCalendar">
          <el-option v-for="p in plans" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </div>
    </div>
    <div class="duty-body">
      <el-table :data="calendarDays" stripe size="small" :span-method="daySpan" border>
        <el-table-column label="周一" width="200">
          <template #default="{row}"><span class="duty-user">{{ row.mon }}</span></template>
        </el-table-column>
        <el-table-column label="周二" width="200">
          <template #default="{row}"><span class="duty-user">{{ row.tue }}</span></template>
        </el-table-column>
        <el-table-column label="周三" width="200">
          <template #default="{row}"><span class="duty-user">{{ row.wed }}</span></template>
        </el-table-column>
        <el-table-column label="周四" width="200">
          <template #default="{row}"><span class="duty-user">{{ row.thu }}</span></template>
        </el-table-column>
        <el-table-column label="周五" width="200">
          <template #default="{row}"><span class="duty-user">{{ row.fri }}</span></template>
        </el-table-column>
        <el-table-column label="周六" width="200">
          <template #default="{row}"><span class="duty-user weekend">{{ row.sat }}</span></template>
        </el-table-column>
        <el-table-column label="周日" width="200">
          <template #default="{row}"><span class="duty-user weekend">{{ row.sun }}</span></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { dutyPlanApi, dutyArrangeApi } from '/@/api/monitor/index'

const year = ref(new Date().getFullYear())
const month = ref(new Date().getMonth() + 1)
const planId = ref<number|null>(null)
const plans = ref<any[]>([])
const calendarDays = ref<any[]>([])
const arranges = ref<any[]>([])

function getWeekRows(year: number, month: number, arranges: any[]) {
  const firstDay = new Date(year, month - 1, 1)
  const lastDay = new Date(year, month, 0)
  const rows: any[] = []
  // 构建日期到值班人映射
  const dutyMap: Record<number, string> = {}
  for (const a of arranges) {
    const start = new Date(a.date_from), end = new Date(a.date_to)
    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      if (d.getMonth() + 1 === month) dutyMap[d.getDate()] = a.user_name
    }
  }
  let current: any = { mon: '', tue: '', wed: '', thu: '', fri: '', sat: '', sun: '' }
  let weekDay = firstDay.getDay()
  if (weekDay === 0) weekDay = 7
  for (let d = 1, dayOfWeek = weekDay; d <= lastDay.getDate(); d++, dayOfWeek++) {
    const name = dutyMap[d] || ''
    if (dayOfWeek === 1) current = { mon: '', tue: '', wed: '', thu: '', fri: '', sat: '', sun: '' }
    const fields = ['', 'mon','tue','wed','thu','fri','sat','sun']
    current[fields[dayOfWeek]] = `${d}日 ${name}`
    if (dayOfWeek === 7 || d === lastDay.getDate()) { rows.push({...current}); dayOfWeek = 0 }
  }
  return rows
}

function daySpan() { return {} }

async function loadPlans() {
  const r = await dutyPlanApi.list()
  plans.value = r.data || []
  if (plans.value.length) { planId.value = plans.value[0].id; loadCalendar() }
}

async function loadCalendar() {
  if (!planId.value) return
  const r = await dutyPlanApi.calendar(planId.value, year.value, month.value)
  arranges.value = r.data?.arranges || []
  calendarDays.value = getWeekRows(year.value, month.value, arranges.value)
}

function prevMonth() { if (month.value === 1) { month.value = 12; year.value-- } else month.value--; loadCalendar() }
function nextMonth() { if (month.value === 12) { month.value = 1; year.value++ } else month.value++; loadCalendar() }

onMounted(() => loadPlans())
</script>

<style scoped>
.duty-page { padding: 20px; }
.duty-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; }
.duty-title { margin:0; font-size:18px; font-weight:600; }
.duty-controls { display:flex; align-items:center; }
.duty-body { background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,0.06); }
.duty-user { font-size:13px; padding:4px 0; }
.weekend { color:#F56C6C; }
</style>
