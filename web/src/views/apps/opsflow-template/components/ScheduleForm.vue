<template>
  <el-dialog
    :title="plan ? '编辑调度' : '新建调度'"
    v-model="visible"
    width="600px"
    top="8vh"
    append-to-body
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="调度名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入调度名称" maxlength="128" />
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input v-model="form.description" placeholder="可选描述" maxlength="255" />
      </el-form-item>
      <el-form-item v-if="!templateId" label="所属模板" prop="template">
        <el-select v-model="form.template" placeholder="选择模板" filterable style="width: 100%">
          <el-option v-for="t in templateOptions" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="调度类型" prop="schedule_type">
        <el-radio-group v-model="form.schedule_type">
          <el-radio label="one_time">一次性</el-radio>
          <el-radio label="cron">周期性</el-radio>
        </el-radio-group>
      </el-form-item>

      <template v-if="form.schedule_type === 'one_time'">
        <el-form-item label="执行时间" prop="scheduled_at">
          <el-date-picker
            v-model="form.scheduled_at"
            type="datetime"
            placeholder="选择执行时间"
            :disabled-date="disabledPastDate"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
      </template>

      <template v-if="form.schedule_type === 'cron'">
        <el-form-item label="频率快捷" prop="cron_preset">
          <el-select v-model="cronPreset" placeholder="选择频率" style="width: 100%" @change="onCronPresetChange">
            <el-option label="每天" value="daily" />
            <el-option label="工作日 (周一至周五)" value="weekdays" />
            <el-option label="每周一" value="monday" />
            <el-option label="每月1号" value="monthly" />
            <el-option label="自定义Cron" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间" prop="cron_time" v-if="cronPreset && cronPreset !== 'custom'">
          <el-time-picker
            v-model="cronTime"
            placeholder="选择时间"
            format="HH:mm"
            value-format="HH:mm"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="Cron表达式" prop="cron_expr" v-if="cronPreset === 'custom'">
          <el-input v-model="form.cron_expr" placeholder="如 0 9 * * 1-5" />
        </el-form-item>
        <el-form-item label="Cron说明" v-if="form.cron_description">
          <el-input :model-value="form.cron_description" disabled />
        </el-form-item>
      </template>

      <el-divider>重试策略（可选）</el-divider>
      <el-form-item label="最大重试" prop="max_retries">
        <el-input-number v-model="form.max_retries" :min="0" :max="10" /> 次
      </el-form-item>
      <el-form-item label="重试间隔" prop="retry_delay" v-if="form.max_retries > 0">
        <el-input-number v-model="form.retry_delay" :min="60" :max="86400" :step="60" /> 秒
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
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
  name: [{ required: true, message: '请输入调度名称', trigger: 'blur' }],
  schedule_type: [{ required: true, message: '请选择调度类型', trigger: 'change' }],
  scheduled_at: [{ required: true, message: '请选择执行时间', trigger: 'change' }],
  cron_expr: [{ required: true, message: '请输入Cron表达式', trigger: 'blur' }],
}

// 初始化编辑数据
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
// 无 templateId 时加载模板列表
watch(visible, (val) => {
  if (val && !props.templateId && !templateOptions.value.length) {
    GetTemplates().then((res: any) => {
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
      form.cron_description = `每天 ${time}`
      break
    case 'weekdays':
      form.cron_expr = `${minute} ${hour} * * 1-5`
      form.cron_description = `工作日 ${time}`
      break
    case 'monday':
      form.cron_expr = `${minute} ${hour} * * 1`
      form.cron_description = `每周一 ${time}`
      break
    case 'monthly':
      form.cron_expr = `${minute} ${hour} 1 * *`
      form.cron_description = `每月1号 ${time}`
      break
  }
}

// 监听时间变化自动更新 cron
watch(cronTime, (val) => {
  if (val && cronPreset.value && cronPreset.value !== 'custom') {
    updateCronFromPreset(cronPreset.value, val)
  }
})

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (!props.templateId && !form.template) {
    ElMessage.warning('请选择所属模板')
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
      ElMessage.success('调度已更新')
    } else {
      await CreateSchedulePlan(data)
      ElMessage.success('调度已创建')
    }
    emit('saved')
    visible.value = false
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  emit('update:modelValue', false)
}
</script>
