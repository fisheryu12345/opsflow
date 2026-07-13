<template>
  <div v-if="templateId" class="task-node-form">
    <GlobalVarInput :model-value="formData" @update:model-value="onVarsChange" :vars="vars" />
    <div class="tnf-actions">
      <el-button type="primary" :loading="submitting" @click="onSubmit">
        {{ $t('message.ticketDetail.taskSubmitExec') }}
      </el-button>
    </div>
  </div>
  <div v-else class="td-action-placeholder">
    <p>{{ $t('message.ticketDetail.taskParamsLoading') }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import GlobalVarInput from '/@/components/GlobalVarInput.vue'
import { loadTemplateVars } from '/@/composables/useTemplateVars'
import { NodeSubmit } from '/@/api/itsm/index'

const props = defineProps<{
  ticketId: number
  node: any
  /** ticket.meta fallback for template_id when node.extras lags behind */
  ticketMeta?: Record<string, any> | null
}>()
const emit = defineEmits<{ submitted: [] }>()
const { t } = useI18n()

const templateId = ref<number | null>(null)
const vars = ref<Record<string, any>>({})
const formData = reactive<Record<string, any>>({})
const submitting = ref(false)

// Resolve the bound OpsFlow template id from the node's extras, falling back to
// ticket.meta._opsflow_params (populated when node payloads lag behind).
watch(
  [() => props.node?.extras?.opsflow_template_id, () => props.ticketMeta],
  () => {
    const tid = props.node?.extras?.opsflow_template_id
      || (props.ticketMeta as any)?._opsflow_params?.template_id
    if (tid && tid !== templateId.value) {
      templateId.value = tid
      loadVars(tid)
    }
  },
  { immediate: true },
)

async function loadVars(tid: number) {
  try {
    const { vars: v, values } = await loadTemplateVars(tid, { coerce: true })
    vars.value = v
    for (const k of Object.keys(formData)) delete formData[k]
    Object.assign(formData, values)
  } catch { vars.value = {} }
}

function onVarsChange(val: Record<string, any>) {
  // GlobalVarInput emits the full object; reconcile so cleared keys are dropped.
  for (const k of Object.keys(formData)) {
    if (!(k in val)) delete formData[k]
  }
  Object.assign(formData, val)
}

async function onSubmit() {
  if (submitting.value) return
  submitting.value = true
  try {
    await NodeSubmit(String(props.ticketId), { state_id: props.node.id, fields: { ...formData } })
    ElMessage.success(t('message.ticketDetail.taskSubmitted'))
    emit('submitted')
  } catch {
    ElMessage.error(t('message.ticketDetail.submitFailed'))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.tnf-actions {
  margin-top: 12px;
  text-align: right;
}
</style>
