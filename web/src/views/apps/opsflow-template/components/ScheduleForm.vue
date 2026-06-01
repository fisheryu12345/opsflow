<template>
  <el-dialog
    :title="plan ? 'Edit Schedule' : 'New Schedule'"
    v-model="visible"
    width="640px"
    top="6vh"
    append-to-body
    :close-on-click-modal="false"
    class="sc-form-dialog"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="sc-form" size="default">
      <!-- Basic Info Section -->
      <div class="sc-form-section">
        <div class="sc-form-section-title">Basic Information</div>
        <el-form-item label="Name" prop="name">
          <el-input v-model="form.name" placeholder="Enter schedule name" maxlength="128" clearable />
        </el-form-item>
        <el-form-item label="Desc" prop="description">
          <el-input v-model="form.description" placeholder="Optional description" maxlength="255" :rows="2" type="textarea" />
        </el-form-item>
        <el-form-item v-if="!templateId" label="Template" prop="template">
          <el-select v-model="form.template" placeholder="Select template" filterable style="width: 100%">
            <el-option v-for="t in templateOptions" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
      </div>

      <!-- Schedule Section -->
      <div class="sc-form-section">
        <div class="sc-form-section-title">Schedule Configuration</div>
        <el-form-item label="Type" prop="schedule_type">
          <el-radio-group v-model="form.schedule_type" class="sc-radio-group">
            <el-radio-button label="one_time">
              <el-icon style="vertical-align: middle; margin-right: 4px"><Clock /></el-icon>One-time
            </el-radio-button>
            <el-radio-button label="cron">
              <el-icon style="vertical-align: middle; margin-right: 4px"><Refresh /></el-icon>Recurring
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="form.schedule_type === 'one_time'">
          <el-form-item label="Run At" prop="scheduled_at">
            <el-date-picker
              v-model="form.scheduled_at"
              type="datetime"
              placeholder="Select execution time"
              :disabled-date="disabledPastDate"
              value-format="YYYY-MM-DDTHH:mm:ss"
              style="width: 100%"
            />
          </el-form-item>
        </template>

        <template v-if="form.schedule_type === 'cron'">
          <el-form-item label="Preset" prop="cron_preset">
            <el-select v-model="cronPreset" placeholder="Select frequency" style="width: 100%" @change="onCronPresetChange">
              <el-option label="Daily" value="daily" />
              <el-option label="Weekdays (Mon-Fri)" value="weekdays" />
              <el-option label="Every Monday" value="monday" />
              <el-option label="Monthly (1st)" value="monthly" />
              <el-option label="Custom Cron" value="custom" />
            </el-select>
          </el-form-item>
          <el-form-item label="Time" prop="cron_time" v-if="cronPreset && cronPreset !== 'custom'">
            <el-time-picker
              v-model="cronTime"
              placeholder="Select time"
              format="HH:mm"
              value-format="HH:mm"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="Cron Expression" prop="cron_expr" v-if="cronPreset === 'custom'">
            <el-input v-model="form.cron_expr" placeholder="e.g. 0 9 * * 1-5" />
          </el-form-item>
          <el-form-item label="Cron Preview" v-if="form.cron_description">
            <el-tag type="info" effect="plain" size="default" style="width: 100%; text-align: left; white-space: normal; line-height: 1.6;">
              <el-icon style="vertical-align: middle; margin-right: 4px"><InfoFilled /></el-icon>{{ form.cron_description }}
            </el-tag>
          </el-form-item>
        </template>
      </div>

      <!-- Retry Section -->
      <div class="sc-form-section">
        <div class="sc-form-section-title">
          Retry Policy
          <el-tag size="small" type="info" effect="plain" style="margin-left: 8px;">Optional</el-tag>
        </div>
        <el-form-item label="Max Retries" prop="max_retries">
          <div class="sc-inline-group">
            <el-input-number v-model="form.max_retries" :min="0" :max="10" controls-position="right" />
            <span class="sc-inline-label">times</span>
          </div>
        </el-form-item>
        <el-form-item label="Retry Delay" prop="retry_delay" v-if="form.max_retries > 0">
          <div class="sc-inline-group">
            <el-input-number v-model="form.retry_delay" :min="60" :max="86400" :step="60" controls-position="right" style="width: 180px" />
            <span class="sc-inline-label">seconds (~{{ Math.round(form.retry_delay / 60) }} min)</span>
          </div>
        </el-form-item>
      </div>
    </el-form>

    <template #footer>
      <div class="sc-dialog-footer">
        <el-button plain @click="visible = false" size="default">Cancel</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit" size="default">
          <el-icon style="vertical-align: middle; margin-right: 4px"><CircleCheck /></el-icon>
          {{ plan ? 'Update Schedule' : 'Create Schedule' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Clock, Refresh, InfoFilled, CircleCheck } from '@element-plus/icons-vue'
import { CreateSchedulePlan, UpdateSchedulePlan } from '/@/api/opsflow/schedule-plans'
import { GetTemplates } from '/@/api/opsflow/templates'

const props = defineProps<{
  modelValue: boolean
  plan?: any | null
  templateId?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'saved'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const formRef = ref()
const submitting = ref(false)
const cronPreset = ref('')
const cronTime = ref('09:00')
const templateOptions = ref<any[]>([])

const form = reactive({
  name: '',
  description: '',
  template: null as number | null,
  schedule_type: 'one_time' as 'one_time' | 'cron',
  scheduled_at: null as string | null,
  cron_expr: '',
  cron_description: '',
  max_retries: 0,
  retry_delay: 300,
})

const rules: Record<string, any> = {
  name: [{ required: true, message: 'Please enter schedule name', trigger: 'blur' }],
  schedule_type: [{ required: true, message: 'Please select schedule type', trigger: 'change' }],
  scheduled_at: [{ required: true, message: 'Please select execution time', trigger: 'change' }],
  cron_expr: [{ required: true, message: 'Please enter cron expression', trigger: 'blur' }],
}

watch(
  () => props.plan,
  (val) => {
    if (val) {
      form.name = val.name || ''
      form.description = val.description || ''
      form.template = val.template ?? null
      form.schedule_type = val.schedule_type || 'one_time'
      form.scheduled_at = val.scheduled_at || null
      form.cron_expr = val.cron_expr || ''
      form.cron_description = val.cron_description || ''
      form.max_retries = val.max_retries ?? 0
      form.retry_delay = val.retry_delay ?? 300
    } else {
      form.template = null
    }
  },
  { immediate: true }
)

watch(visible, (val) => {
  if (val && !props.templateId && !templateOptions.value.length) {
    GetTemplates({is_draft: false, limit: 999}).then((res: any) => {
      templateOptions.value = res.data || res.results || []
    }).catch(() => {})
  }
})

function disabledPastDate(time: Date) {
  return time.getTime() < Date.now() - 86400000
}

function onCronPresetChange(val: string) {
  if (val && val !== 'custom' && cronTime.value) {
    updateCronFromPreset(val, cronTime.value)
  }
}

function updateCronFromPreset(preset: string, time: string) {
  const [hour, minute] = time.split(':')
  switch (preset) {
    case 'daily':
      form.cron_expr = `${minute} ${hour} * * *`
      form.cron_description = `Daily ${time}`
      break
    case 'weekdays':
      form.cron_expr = `${minute} ${hour} * * 1-5`
      form.cron_description = `Weekdays ${time}`
      break
    case 'monday':
      form.cron_expr = `${minute} ${hour} * * 1`
      form.cron_description = `Monday ${time}`
      break
    case 'monthly':
      form.cron_expr = `${minute} ${hour} 1 * *`
      form.cron_description = `Monthly 1st ${time}`
      break
  }
}

watch(cronTime, (val) => {
  if (val && cronPreset.value && cronPreset.value !== 'custom') {
    updateCronFromPreset(cronPreset.value, val)
  }
})

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (!props.templateId && !form.template) {
    ElMessage.warning('Please select a template')
    return
  }
  submitting.value = true
  try {
    const data: any = {
      template: props.templateId ?? form.template,
      name: form.name,
      description: form.description,
      schedule_type: form.schedule_type,
      max_retries: form.max_retries,
      retry_delay: form.retry_delay,
    }

    if (form.schedule_type === 'one_time') {
      data.scheduled_at = form.scheduled_at
    } else {
      data.cron_expr = form.cron_expr
      data.cron_description = form.cron_description
    }

    if (props.plan?.id) {
      await UpdateSchedulePlan(props.plan.id, data)
      ElMessage.success('Schedule updated')
    } else {
      await CreateSchedulePlan(data)
      ElMessage.success('Schedule created')
    }
    emit('saved')
    visible.value = false
  } catch (e: any) {
    const errData = e?.response?.data
    const errMsg = errData?.template?.[0] || errData?.msg || e?.message || 'Operation failed'
    ElMessage.error(errMsg)
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  emit('update:modelValue', false)
}
</script>

<style scoped>
/* Dialog base */
.sc-form-dialog :deep(.el-dialog__body) {
  padding: 0;
}
.sc-form-dialog :deep(.el-dialog__footer) {
  padding: 0;
}

/* Form */
.sc-form {
  padding: 4px 24px 4px;
}
.sc-form-section {
  margin-bottom: 18px;
}
.sc-form-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
  padding: 12px 0 8px 8px;
  border-bottom: 1px solid #f5f5f5;
  display: flex;
  align-items: center;
}
.sc-form-section-title .el-tag {
  font-size: 11px;
  font-weight: 400;
}

/* Radio group styled as buttons */
.sc-radio-group :deep(.el-radio-button__inner) {
  border-radius: 8px !important;
  padding: 6px 18px;
  font-size: 13px;
  border: 1px solid #dcdfe6;
  background: #fff;
}
.sc-radio-group :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 8px 0 0 8px !important;
  border-right: none;
}
.sc-radio-group :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 8px 8px 0 !important;
}
.sc-radio-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #409eff 0%, #7ec1ff 100%);
  border-color: #409eff;
  color: #fff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.25);
}

/* Inline group (input-number + label) */
.sc-inline-group {
  display: flex;
  align-items: center;
  gap: 10px;
}
.sc-inline-label {
  font-size: 13px;
  color: #909399;
}

/* Form item refinements */
.sc-form :deep(.el-form-item) {
  margin-bottom: 18px;
}
.sc-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #303133;
  font-size: 13px;
}
.sc-form :deep(.el-input__wrapper),
.sc-form :deep(.el-textarea__inner) {
  border-radius: 8px;
}
.sc-form :deep(.el-select) {
  width: 100%;
}

/* Footer */
.sc-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 24px 20px;
  border-top: 1px solid #f0f0f0;
  background: #fafbfc;
  border-radius: 0 0 14px 14px;
}
.sc-dialog-footer .el-button {
  border-radius: 8px;
  padding: 9px 22px;
  font-weight: 500;
}
.sc-dialog-footer .el-button--primary {
  box-shadow: 0 4px 12px rgba(64,158,255,0.3);
}
</style>
