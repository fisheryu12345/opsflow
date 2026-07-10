<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="onClose"
    :title="schedule ? $t('message.slaSchedule.editSchedule') : $t('message.slaSchedule.newSchedule')"
    width="720px" top="8vh" destroy-on-close append-to-body
  >
    <el-form :model="form" label-width="100px" size="small">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item :label="$t('message.slaSchedule.scheduleName')">
            <el-input v-model="form.name" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="$t('message.slaSchedule.scheduleNameEn')">
            <el-input v-model="form.name_en" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item :label="$t('message.slaSchedule.scheduleProject')">
        <el-select v-model="form.project" clearable :placeholder="$t('message.slaSchedule.globalProject')" style="width:100%">
          <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>
    </el-form>

    <!-- Day Type Tabs -->
    <el-tabs v-model="activeTab">
      <el-tab-pane :label="$t('message.slaSchedule.workingDays')" name="days">
        <DayList
          type="NORMAL"
          :items="localDays"
          :week-day-map="weekDayMap"
          @add="onAddDay('NORMAL')"
          @remove="(i: number) => localDays.splice(i, 1)"
          @update:item="(i: number, v: any) => localDays[i] = v"
        />
      </el-tab-pane>
      <el-tab-pane :label="$t('message.slaSchedule.overtimeDays')" name="workdays">
        <DayList
          type="WORKDAY"
          :items="localWorkdays"
          @add="onAddDay('WORKDAY')"
          @remove="(i: number) => localWorkdays.splice(i, 1)"
          @update:item="(i: number, v: any) => localWorkdays[i] = v"
        />
      </el-tab-pane>
      <el-tab-pane :label="$t('message.slaSchedule.holidays')" name="holidays">
        <DayList
          type="HOLIDAY"
          :items="localHolidays"
          @add="onAddDay('HOLIDAY')"
          @remove="(i: number) => localHolidays.splice(i, 1)"
          @update:item="(i: number, v: any) => localHolidays[i] = v"
        />
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="onClose">{{ $t('message.common.cancel') }}</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">{{ $t('message.common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useProjectStore } from '/@/stores/project'
import { scheduleApi, dayApi, durationApi } from '/@/api/itsm/index'
import DayList from './ScheduleDayList.vue'

const props = defineProps<{
  modelValue: boolean
  schedule?: any | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'saved': []
}>()

const { t } = useI18n()
const projectStore = useProjectStore()

const saving = ref(false)
const activeTab = ref('days')

const form = ref({ name: '', name_en: '', project: null as number | null })
const localDays = ref<any[]>([])
const localWorkdays = ref<any[]>([])
const localHolidays = ref<any[]>([])

const projectList = computed(() => projectStore.myProjects || [])

const weekDayMap: Record<string, string> = {
  '0': t('message.slaSchedule.weekDays.0'),
  '1': t('message.slaSchedule.weekDays.1'),
  '2': t('message.slaSchedule.weekDays.2'),
  '3': t('message.slaSchedule.weekDays.3'),
  '4': t('message.slaSchedule.weekDays.4'),
  '5': t('message.slaSchedule.weekDays.5'),
  '6': t('message.slaSchedule.weekDays.6'),
}

function makeEmptyDay(type: string): any {
  return {
    name: '', name_en: '', type_of_day: type,
    day_of_week: type === 'NORMAL' ? '0,1,2,3,4' : '-1',
    start_date: null, end_date: null,
    durations: [],
  }
}

function onAddDay(type: string) {
  if (type === 'NORMAL') localDays.value.push(makeEmptyDay('NORMAL'))
  else if (type === 'WORKDAY') localWorkdays.value.push(makeEmptyDay('WORKDAY'))
  else localHolidays.value.push(makeEmptyDay('HOLIDAY'))
}

// Populate form when editing existing schedule
watch(() => props.schedule, (s) => {
  if (s) {
    form.value = {
      name: s.name || '',
      name_en: s.name_en || '',
      project: s.project || null,
    }
    localDays.value = (s.days || []).map((d: any) => ({ ...d }))
    localWorkdays.value = (s.workdays || []).map((d: any) => ({ ...d }))
    localHolidays.value = (s.holidays || []).map((d: any) => ({ ...d }))
  } else {
    form.value = { name: '', name_en: '', project: null }
    localDays.value = []
    localWorkdays.value = []
    localHolidays.value = []
  }
}, { immediate: true })

function onClose() {
  emit('update:modelValue', false)
}

// Save a single Day (create or update) and return its ID
async function saveDay(day: any): Promise<number> {
  // Create new durations first, collect all duration IDs
  const durationIds: number[] = []
  if (day.durations && day.durations.length > 0) {
    for (const dur of day.durations) {
      const dName = dur.name
      if (!dName) continue // skip empty durations
      if (dur.id) {
        // Update existing duration
        await durationApi.update(dur.id, {
          name: dName, name_en: dur.name_en || '',
          start_time: dur.start_time || '09:00:00',
          end_time: dur.end_time || '18:00:00',
        })
        durationIds.push(dur.id)
      } else {
        // Create new duration
        const dRes: any = await durationApi.create({
          name: dName, name_en: dur.name_en || '',
          start_time: dur.start_time || '09:00:00',
          end_time: dur.end_time || '18:00:00',
        })
        durationIds.push((dRes as any)?.data?.id || (dRes as any)?.id)
      }
    }
  }

  const payload: any = {
    name: day.name, name_en: day.name_en || '',
    type_of_day: day.type_of_day,
    day_of_week: day.day_of_week || '-1',
    start_date: day.start_date || null,
    end_date: day.end_date || null,
    duration_ids: durationIds,
  }

  if (day.id) {
    await dayApi.update(day.id, payload)
    return day.id
  } else {
    const res: any = await dayApi.create(payload)
    return (res as any)?.data?.id || (res as any)?.id
  }
}

async function onSave() {
  if (!form.value.name) {
    ElMessage.warning('请输入排班名称')
    return
  }
  saving.value = true
  try {
    // Save all Days first
    const daysIds: number[] = []
    for (const d of localDays.value) {
      const id = await saveDay({ ...d, type_of_day: 'NORMAL' })
      daysIds.push(id)
    }
    const workdayIds: number[] = []
    for (const d of localWorkdays.value) {
      const id = await saveDay({ ...d, type_of_day: 'WORKDAY' })
      workdayIds.push(id)
    }
    const holidayIds: number[] = []
    for (const d of localHolidays.value) {
      const id = await saveDay({ ...d, type_of_day: 'HOLIDAY' })
      holidayIds.push(id)
    }

    // Save Schedule
    const schedulePayload: any = {
      name: form.value.name,
      name_en: form.value.name_en || '',
      project: form.value.project || null,
      day_ids: daysIds,
      workday_ids: workdayIds,
      holiday_ids: holidayIds,
    }

    if (props.schedule?.id) {
      await scheduleApi.update(props.schedule.id, schedulePayload)
    } else {
      await scheduleApi.create(schedulePayload)
    }

    ElMessage.success(t('message.common.saveSuccess'))
    emit('saved')
  } catch {
    ElMessage.error(t('message.common.saveFailed'))
  } finally {
    saving.value = false
  }
}

// Fetch project list
onMounted(async () => {
  if (projectList.value.length === 0) {
    await projectStore.fetchMyProjects()
  }
})
</script>
