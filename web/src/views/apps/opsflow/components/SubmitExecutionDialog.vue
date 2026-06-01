<template>
  <el-dialog v-model="visible" title="Submit Execution" width="560px" top="8vh" class="submit-exec-dialog">
    <div v-if="loading" v-loading="loading" class="dialog-loading" />
    <template v-else>
      <div class="dialog-template-name">
        <span class="dialog-tpl-label">Template:</span>
        <span class="dialog-tpl-value">{{ templateName || 'Unknown' }}</span>
      </div>

      <div v-if="templateVarsKeys.length > 0" class="dialog-vars-section">
        <div class="dialog-section-header">Parameters</div>
        <div class="dialog-vars-hint">Fill in the parameters for this execution. Values are saved as overrides and do not affect the template.</div>
        <div class="vars-grid">
          <div v-for="key in templateVarsKeys" :key="key" class="var-row">
            <div class="var-label">
              <span class="var-key">{{ key }}</span>
              <el-tag size="small" effect="plain" class="var-type-tag">{{ varTypeLabel(templateVars[key]?.type) }}</el-tag>
              <span v-if="templateVars[key]?.description" class="var-desc">{{ templateVars[key].description }}</span>
            </div>
            <el-input
              v-model="overrides[key]"
              :type="inputType(templateVars[key]?.type)"
              :rows="templateVars[key]?.type === 'textarea' ? 2 : 1"
              :placeholder="defaultPlaceholder(templateVars[key])"
              size="small"
            />
          </div>
        </div>
      </div>

      <div v-else class="dialog-no-vars">
        <el-empty description="No parameters defined in this template" :image-size="40" />
      </div>
    </template>

    <template #footer>
      <el-button size="small" @click="visible = false">Cancel</el-button>
      <el-button size="small" type="primary" :loading="submitting" :disabled="submitting" @click="onSubmit">
        <el-icon><VideoPlay /></el-icon> Submit (Pending)
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay } from '@element-plus/icons-vue'
import { GetGlobalVariables } from '/@/api/opsflow/templates'
import { CreateExecution } from '/@/api/opsflow/executions'

const props = defineProps<{
  modelValue: boolean
  templateId: number | null
  templateName?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'execution-created': [execId: number]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const submitting = ref(false)
const templateVars = ref<Record<string, any>>({})
const overrides = ref<Record<string, any>>({})

const templateVarsKeys = computed(() => Object.keys(templateVars.value))

function varTypeLabel(t?: string) {
  const m: Record<string, string> = { input: 'Text', textarea: 'Textarea', password: 'Password', int: 'Number', float: 'Float' }
  return m[t || ''] || t || 'Text'
}

function inputType(t?: string) {
  if (t === 'password') return 'password'
  if (t === 'textarea') return 'textarea'
  return 'text'
}

function defaultPlaceholder(info: any) {
  const val = info?.value
  if (val !== undefined && val !== null && val !== '') return String(val)
  return 'Enter value...'
}

async function fetchVars() {
  if (!props.templateId) return
  loading.value = true
  try {
    const res = await GetGlobalVariables(props.templateId)
    const data = res.data?.data || {}
    templateVars.value = {}
    overrides.value = {}
    for (const [key, val] of Object.entries(data)) {
      if (typeof val === 'object' && val !== null && 'value' in (val as any)) {
        templateVars.value[key] = val
      } else {
        templateVars.value[key] = { value: val, type: 'input', description: '' }
      }
    }
  } catch {
    ElMessage.error('Failed to load template variables')
  }
  loading.value = false
}

async function onSubmit() {
  if (!props.templateId) return
  submitting.value = true
  try {
    // Only include overrides that differ from the default
    const variableOverrides: Record<string, any> = {}
    for (const key of templateVarsKeys.value) {
      const ov = overrides.value[key]
      const def = templateVars.value[key]?.value
      if (ov !== undefined && ov !== null && ov !== def) {
        variableOverrides[key] = ov
      }
    }

    const res = await CreateExecution({
      template: props.templateId,
      variable_overrides: variableOverrides,
      status: 'pending_approval',
    })

    const exec = res.data?.data || res.data
    if (exec?.id) {
      ElMessage.success(`Execution created (ID: ${exec.id})`)
      visible.value = false
      emit('execution-created', exec.id)
    }
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || 'Failed to create execution')
  }
  submitting.value = false
}

watch(() => props.modelValue, (v) => {
  if (v) {
    templateVars.value = {}
    overrides.value = {}
    fetchVars()
  }
})
</script>

<style scoped>
.submit-exec-dialog :deep(.el-dialog__body) { padding-top: 8px; }
.dialog-loading { min-height: 200px; display: flex; align-items: center; justify-content: center; }
.dialog-template-name { display: flex; align-items: center; gap: 8px; padding: 12px 0; border-bottom: 1px solid #f0f0f0; margin-bottom: 16px; }
.dialog-tpl-label { font-size: 12px; color: #909399; }
.dialog-tpl-value { font-size: 13px; font-weight: 600; color: #303133; }
.dialog-section-header { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 4px; }
.dialog-vars-hint { font-size: 11px; color: #909399; margin-bottom: 12px; }
.dialog-vars-section { margin-top: 4px; }
.dialog-no-vars { padding: 20px 0; }
.vars-grid { display: flex; flex-direction: column; gap: 10px; max-height: 320px; overflow-y: auto; }
.var-row { display: flex; flex-direction: column; gap: 4px; padding: 8px 10px; background: #fafafa; border-radius: 8px; }
.var-label { display: flex; align-items: center; gap: 6px; }
.var-key { font-family: monospace; font-size: 13px; font-weight: 600; color: #303133; }
.var-type-tag { font-size: 10px; }
.var-desc { font-size: 11px; color: #c0c4cc; margin-left: auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
