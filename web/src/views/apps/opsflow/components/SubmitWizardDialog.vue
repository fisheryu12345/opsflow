<template>
  <el-dialog
    v-model="visible"
    title="Submit Execution Wizard"
    width="960px"
    top="4vh"
    :close-on-click-modal="false"
    class="wizard-dialog"
    @close="handleClose"
  >
    <!-- Step Progress -->
    <div class="wizard-steps">
      <el-steps :active="activeStep" align-center finish-status="success" :space="180">
        <el-step title="① Validation" description="Pipeline Check" />
        <el-step title="② Change" description="Link Change Request" />
        <el-step title="③ Params" description="Variables" />
        <el-step title="④ Risk" description="AI Analysis & Confirm" />
        <el-step title="⑤ Schedule" description="Timing Strategy" />
      </el-steps>
    </div>

    <el-divider style="margin: 16px 0 20px" />

    <div class="wizard-body" v-loading="stepLoading">
      <!-- ==================== Step 1: Validation ==================== -->
      <div v-show="activeStep === 0" class="step-content">
        <div class="step-header">
          <div class="step-icon">🔍</div>
          <div>
            <h3 class="step-title">Pipeline 构型校验</h3>
            <p class="step-desc">校验流程拓扑结构、节点配置、引擎兼容性</p>
          </div>
        </div>

        <!-- Pipeline Stats -->
        <div class="stats-row">
          <div class="stat-card">
            <div class="stat-value">{{ pipelineNodes.length }}</div>
            <div class="stat-label">Nodes</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ pipelineEdges.length }}</div>
            <div class="stat-label">Edges</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ atomTypesCount }}</div>
            <div class="stat-label">Atom Types</div>
          </div>
        </div>

        <div class="step-action" v-if="!validationResult">
          <el-button type="primary" size="default" :loading="stepLoading" @click="runValidation" :icon="Search">
            Run Validation
          </el-button>
          <span class="action-hint">调用 DeepSeek 分析流程结构合规性</span>
        </div>

        <!-- Validation Results -->
        <div v-if="validationResult" class="result-section">
          <div class="result-card result-pass" v-if="!validationResult.hasErrors">
            <div class="result-icon">✅</div>
            <div>
              <div class="result-title">结构验证通过</div>
              <div class="result-desc">拓扑完整，无孤立节点，网关路径正确，兼容 Bamboo 引擎</div>
            </div>
          </div>

          <div class="result-card result-warn" v-for="(w, i) in validationResult.warnings" :key="'w'+i">
            <div class="result-icon">⚠️</div>
            <div>
              <div class="result-title">Warning</div>
              <div class="result-desc">{{ w }}</div>
            </div>
          </div>

          <div class="result-card result-error" v-for="(e, i) in validationResult.errors" :key="'e'+i">
            <div class="result-icon">❌</div>
            <div>
              <div class="result-title">Error</div>
              <div class="result-desc">{{ e }}</div>
            </div>
          </div>

          <div v-if="validationResult.suggestions?.length" class="suggestion-box">
            <div class="suggestion-title">💡 Suggestions</div>
            <ul class="suggestion-list">
              <li v-for="(s, i) in validationResult.suggestions" :key="i">{{ s }}</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- ==================== Step 2: Change Request ==================== -->
      <div v-show="activeStep === 1" class="step-content">
        <div class="step-header">
          <div class="step-icon">📋</div>
          <div>
            <h3 class="step-title">关联 ServiceNow Change Request</h3>
            <p class="step-desc">选择与此流程关联的变更单</p>
          </div>
        </div>

        <div class="cr-selector" v-loading="crLoading">
          <el-select
            v-model="selectedCr"
            placeholder="请选择 Change Request ..."
            filterable
            value-key="cr_number"
            style="width:100%"
            size="default"
            @change="onCrChange"
          >
            <el-option
              v-for="cr in crList"
              :key="cr.cr_number"
              :label="`${cr.cr_number} - ${cr.title}`"
              :value="cr"
            >
              <div class="cr-option">
                <div class="cr-option-top">
                  <span class="cr-number">{{ cr.cr_number }}</span>
                  <span class="cr-status" :class="cr.status">{{ cr.status === 'approved' ? 'Approved' : 'Pending' }}</span>
                </div>
                <div class="cr-option-title">{{ cr.title }}</div>
                <div class="cr-option-meta">
                  <span>{{ cr.requester }}</span>
                  <span>{{ cr.change_window_start }} ~ {{ cr.change_window_end }}</span>
                </div>
              </div>
            </el-option>
          </el-select>
        </div>

        <!-- Selected CR Detail -->
        <div v-if="selectedCr" class="cr-detail-card">
          <div class="cr-detail-row">
            <span class="cr-detail-label">CR Number</span>
            <span class="cr-detail-value"><strong>{{ selectedCr.cr_number }}</strong></span>
          </div>
          <div class="cr-detail-row">
            <span class="cr-detail-label">Title</span>
            <span class="cr-detail-value">{{ selectedCr.title }}</span>
          </div>
          <div class="cr-detail-row">
            <span class="cr-detail-label">Status</span>
            <span class="cr-detail-value">
              <el-tag :type="selectedCr.status === 'approved' ? 'success' : 'warning'" size="small">
                {{ selectedCr.status === 'approved' ? 'Approved' : 'Pending' }}
              </el-tag>
            </span>
          </div>
          <div class="cr-detail-row">
            <span class="cr-detail-label">Change Window</span>
            <span class="cr-detail-value">{{ selectedCr.change_window_start }} ~ {{ selectedCr.change_window_end }}</span>
          </div>
          <div class="cr-detail-row">
            <span class="cr-detail-label">Requester</span>
            <span class="cr-detail-value">{{ selectedCr.requester }}</span>
          </div>
          <div class="cr-detail-row cr-detail-desc">
            <span class="cr-detail-label">Description</span>
            <span class="cr-detail-value">{{ selectedCr.description }}</span>
          </div>
        </div>
      </div>

      <!-- ==================== Step 3: Parameters ==================== -->
      <div v-show="activeStep === 2" class="step-content">
        <div class="step-header">
          <div class="step-icon">⚙️</div>
          <div>
            <h3 class="step-title">参数与变量配置</h3>
            <p class="step-desc">设置流程执行所需的变量参数，仅需修改需要覆盖的默认值</p>
          </div>
        </div>

        <div v-if="templateVarsKeys.length === 0" class="no-vars">
          <el-empty description="No parameters defined in this template" :image-size="40" />
        </div>
        <div v-else class="vars-grid">
          <div v-for="key in templateVarsKeys" :key="key" class="var-row">
            <div class="var-header">
              <div class="var-info">
                <span class="var-key">{{ key }}</span>
                <el-tag size="small" effect="plain" class="var-type-tag">{{ varTypeLabel(templateVars[key]?.type) }}</el-tag>
              </div>
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

      <!-- ==================== Step 4: Risk Analysis ==================== -->
      <div v-show="activeStep === 3" class="step-content">
        <div class="step-header">
          <div class="step-icon">🛡️</div>
          <div>
            <h3 class="step-title">AI 风险分析与确认</h3>
            <p class="step-desc">调用 DeepSeek 分析变更影响并逐条确认风险</p>
          </div>
        </div>

        <div class="step-action" v-if="!riskResult">
          <el-button type="warning" size="default" :loading="riskLoading" @click="runRiskAnalysis" :icon="Aim">
            Execute Risk Analysis
          </el-button>
          <span class="action-hint">调用 DeepSeek 分析变更影响与风险</span>
        </div>

        <div v-if="riskResult" class="result-section">
          <!-- Summary -->
          <div class="analysis-card">
            <div class="card-title">📋 变更概要</div>
            <div class="card-body">{{ riskResult.summary }}</div>
          </div>

          <!-- Risk Items -->
          <div class="analysis-card" v-if="riskResult.risks?.length">
            <div class="card-title">⚠️ 风险项（请逐条确认）</div>
            <div
              v-for="(risk, i) in riskResult.risks"
              :key="i"
              class="risk-item"
              :class="'risk-' + (risk.level || 'low')"
            >
              <el-checkbox v-model="riskChecked[i]" @change="onRiskCheckChange">
                <div class="risk-content">
                  <el-tag
                    :type="risk.level === 'high' ? 'danger' : risk.level === 'medium' ? 'warning' : 'info'"
                    size="small"
                    effect="dark"
                  >
                    {{ risk.level === 'high' ? '高' : risk.level === 'medium' ? '中' : '低' }}
                  </el-tag>
                  <span class="risk-text">{{ risk.text }}</span>
                </div>
              </el-checkbox>
            </div>
          </div>

          <!-- Suggestions -->
          <div class="analysis-card suggestion-card" v-if="riskResult.suggestions?.length">
            <div class="card-title">💡 建议</div>
            <ul class="suggestion-list">
              <li v-for="(s, i) in riskResult.suggestions" :key="i">{{ s }}</li>
            </ul>
          </div>

          <!-- Overall Confirm -->
          <div class="confirm-bar">
            <el-checkbox v-model="riskConfirmed">
              <span class="confirm-text">
                <strong>我已知晓上述所有风险</strong>，并确认执行此变更流程。如因未勾选的风险项导致问题，由我承担相应责任。
              </span>
            </el-checkbox>
          </div>
        </div>

        <div v-if="stepError" class="step-error">
          <el-alert :title="stepError" type="error" show-icon :closable="false" />
        </div>
      </div>

      <!-- ==================== Step 5: Schedule ==================== -->
      <div v-show="activeStep === 4" class="step-content">
        <div class="step-header">
          <div class="step-icon">⏰</div>
          <div>
            <h3 class="step-title">定时执行策略</h3>
            <p class="step-desc">设置审批通过后的执行策略</p>
          </div>
        </div>

        <div class="schedule-option">
          <el-radio-group v-model="scheduleType" class="schedule-radios">
            <el-radio value="timed" class="schedule-radio-item">
              <div class="radio-content">
                <div class="radio-title">✅ 定时执行</div>
                <div class="radio-desc">审批通过后，在指定时间自动执行</div>
              </div>
            </el-radio>
            <el-radio value="manual" class="schedule-radio-item">
              <div class="radio-content">
                <div class="radio-title">❌ 手动触发</div>
                <div class="radio-desc">待 Change 在 ServiceNow 审批完毕后，在此处手动启动执行</div>
              </div>
            </el-radio>
          </el-radio-group>
        </div>

        <template v-if="scheduleType === 'timed'">
          <div class="schedule-picker">
            <div class="picker-row">
              <div class="picker-field">
                <label class="picker-label">执行日期</label>
                <el-date-picker
                  v-model="scheduledDate"
                  type="date"
                  placeholder="Select date"
                  :disabled-date="disabledDate"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                />
              </div>
              <div class="picker-field">
                <label class="picker-label">执行时间</label>
                <el-time-picker
                  v-model="scheduledTime"
                  placeholder="Select time"
                  format="HH:mm"
                  value-format="HH:mm"
                  :disabled-hours="disabledHours"
                  :disabled-minutes="disabledMinutes"
                  style="width: 100%"
                />
              </div>
            </div>

            <div class="window-hint" v-if="selectedCr">
              <el-icon><InfoFilled /></el-icon>
              <span>Change 窗口：{{ selectedCr.change_window_start }} ~ {{ selectedCr.change_window_end }}，可选执行时间范围 {{ windowStart }} ~ {{ windowEndExclusive }}</span>
            </div>

            <div class="cancel-warning">
              <el-icon style="color:#F56C6C"><WarningFilled /></el-icon>
              <span>如到达执行时间前 30 分钟仍未审批，该定时任务将<strong>自动取消</strong>。请确保审批流程及时完成。</span>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="manual-hint">
            <el-icon style="color:#409EFF"><InfoFilled /></el-icon>
            <span>创建 Execution（状态: <code>pending_approval</code>），待 ServiceNow 审批完成后在此处手动启动执行。</span>
          </div>
        </template>
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <div class="wizard-footer">
        <div class="footer-left">
          <el-button v-if="activeStep > 0" text size="default" @click="prevStep">
            ← Back
          </el-button>
        </div>
        <div class="footer-right">
          <el-button plain size="default" @click="visible = false">Cancel</el-button>
          <el-button
            v-if="activeStep < 4"
            type="primary"
            size="default"
            :disabled="!canNext"
            @click="nextStep"
          >
            Continue →
          </el-button>
          <el-button
            v-else
            type="primary"
            size="default"
            :loading="submitting"
            :disabled="!canSubmit"
            @click="handleSubmit"
          >
            <el-icon><CircleCheck /></el-icon> Submit
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Aim, CircleCheck, InfoFilled, WarningFilled } from '@element-plus/icons-vue'
import { GetGlobalVariables, AnalyzePipeline } from '/@/api/opsflow/templates'
import { CreateExecution } from '/@/api/opsflow/executions'
import { CreateSchedulePlan } from '/@/api/opsflow/schedule-plans'
import { GetServicenowChangeRequests } from '/@/api/opsflow/servicenow'

const props = defineProps<{
  modelValue: boolean
  templateId: number | null
  templateName?: string
  pipelineNodes?: any[]
  pipelineEdges?: any[]
}>()

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'execution-created': [execId: number]
}>()

// ---------- Dialog State ----------
const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const activeStep = ref(0)
const stepLoading = ref(false)
const riskLoading = ref(false)
const stepError = ref('')
const submitting = ref(false)

// ---------- Step 1: Validation ----------
const validationResult = ref<any>(null)

const atomTypesCount = computed(() => {
  const types = new Set((props.pipelineNodes || []).map((n: any) => n.atom_type).filter(Boolean))
  return types.size
})

async function runValidation() {
  if (!props.pipelineNodes?.length) {
    ElMessage.warning('No nodes to validate')
    return
  }
  stepLoading.value = true
  stepError.value = ''
  try {
    const res = await AnalyzePipeline({ nodes: props.pipelineNodes, edges: props.pipelineEdges || [] })
    validationResult.value = res.data?.data || res.data
  } catch (e: any) {
    stepError.value = e?.msg || e?.message || 'Validation failed'
  } finally {
    stepLoading.value = false
  }
}

// ---------- Step 2: Change Request ----------
const crList = ref<any[]>([])
const crLoading = ref(false)
const selectedCr = ref<any>(null)
const windowStart = computed(() => selectedCr.value?.change_window_start?.split(' ')[1] || '--:--')
const windowEndExclusive = computed(() => {
  if (!selectedCr.value?.change_window_end) return '--:--'
  // Subtract 1 hour for the exclusive end
  const parts = selectedCr.value.change_window_end.split(' ')
  const timeParts = (parts[1] || '00:00').split(':')
  let h = parseInt(timeParts[0]) - 1
  return String(h).padStart(2, '0') + ':' + (timeParts[1] || '00')
})

async function loadCrList() {
  crLoading.value = true
  try {
    const res = await GetServicenowChangeRequests()
    crList.value = res?.data || []
  } catch {
    crList.value = []
    ElMessage.error('Failed to load change requests')
  } finally {
    crLoading.value = false
  }
}

function onCrChange(val: any) {
  selectedCr.value = val
}

// ---------- Step 3: Parameters ----------
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

async function loadVars() {
  if (!props.templateId) return
  try {
    const res = await GetGlobalVariables(props.templateId)
    const data = res.data || {}
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
    // silent
  }
}

// ---------- Step 4: Risk Analysis ----------
const riskResult = ref<any>(null)
const riskChecked = ref<boolean[]>([])
const riskConfirmed = ref(false)

async function runRiskAnalysis() {
  if (!props.pipelineNodes?.length) return
  riskLoading.value = true
  stepError.value = ''
  try {
    const res = await AnalyzePipeline({ nodes: props.pipelineNodes, edges: props.pipelineEdges || [] })
    riskResult.value = res.data?.data || res.data
    riskChecked.value = (riskResult.value?.risks || []).map(() => false)
    riskConfirmed.value = false
  } catch (e: any) {
    stepError.value = e?.msg || e?.message || 'Risk analysis failed'
  } finally {
    riskLoading.value = false
  }
}

function onRiskCheckChange() {
  // recompute button state reactively
}

const allRisksChecked = computed(() => {
  if (!riskResult.value?.risks?.length) return true
  return riskChecked.value.length > 0 && riskChecked.value.every(Boolean)
})

// ---------- Step 5: Schedule ----------
const scheduleType = ref<'timed' | 'manual'>('manual')
const scheduledDate = ref('')
const scheduledTime = ref('')

function disabledDate(time: Date) {
  if (!selectedCr.value) return false
  const start = new Date(selectedCr.value.change_window_start)
  const end = new Date(selectedCr.value.change_window_end)
  return time < start || time > end
}

function disabledHours() {
  if (!selectedCr.value) return []
  const startParts = (selectedCr.value.change_window_start?.split(' ')[1] || '00:00').split(':')
  const endParts = (selectedCr.value.change_window_end?.split(' ')[1] || '23:59').split(':')
  const startH = parseInt(startParts[0])
  const endH = parseInt(endParts[0])
  const hours: number[] = []
  for (let h = 0; h < 24; h++) {
    if (h < startH || h > endH) hours.push(h)
  }
  return hours
}

function disabledMinutes() {
  return []
}

// ---------- Navigation ----------
const canNext = computed(() => {
  switch (activeStep.value) {
    case 0: return validationResult.value !== null && !stepError.value
    case 1: return selectedCr.value !== null
    case 2: return true
    case 3: return riskResult.value !== null && allRisksChecked.value && riskConfirmed.value
    default: return true
  }
})

const canSubmit = computed(() => {
  if (scheduleType.value === 'timed') {
    return scheduledDate.value && scheduledTime.value
  }
  return true
})

function nextStep() {
  if (activeStep.value === 1 && !crList.value.length) {
    loadCrList()
  }
  if (activeStep.value === 2) {
    // Load vars if not loaded
    if (!templateVarsKeys.value.length) loadVars()
  }
  if (activeStep.value < 4) {
    activeStep.value++
  }
}

function prevStep() {
  if (activeStep.value > 0) {
    activeStep.value--
  }
}

// ---------- Submit ----------
function buildVariableOverrides(): Record<string, any> {
  const vars: Record<string, any> = {}
  for (const key of templateVarsKeys.value) {
    const ov = overrides.value[key]
    const def = templateVars.value[key]?.value
    if (ov !== undefined && ov !== null && ov !== def) {
      vars[key] = ov
    }
  }
  return vars
}

async function handleSubmit() {
  if (!props.templateId) return
  submitting.value = true
  try {
    // Build context with CR and risk info
    const context: Record<string, any> = {}
    if (selectedCr.value) {
      context.cr_number = selectedCr.value.cr_number
      context.cr_title = selectedCr.value.title
      context.cr_status = selectedCr.value.status
    }
    context.risk_confirmed = riskConfirmed.value
    context.pipeline_validated = !!validationResult.value

    // If timed schedule, create schedule plan first, then link to execution
    let scheduleId: number | null = null
    if (scheduleType.value === 'timed' && scheduledDate.value && scheduledTime.value) {
      const scheduleRes = await CreateSchedulePlan({
        template: props.templateId,
        name: `Auto: ${selectedCr.value?.cr_number || ''} ${scheduledDate.value} ${scheduledTime.value}`,
        description: `Auto-created from submission wizard for CR ${selectedCr.value?.cr_number || ''}`,
        schedule_type: 'one_time',
        scheduled_at: `${scheduledDate.value}T${scheduledTime.value}:00`,
        max_retries: 0,
      })
      scheduleId = scheduleRes.data?.data?.id || scheduleRes.data?.id
    }

    // Determine execution status based on CR approval
    // If CR is already approved, set to pending (ready to start)
    // If CR is still pending, set to pending_approval (waiting for approval)
    const execStatus = selectedCr.value?.status === 'approved' ? 'pending' : 'pending_approval'

    // Create execution (with schedule_plan FK if available)
    const execData: Record<string, any> = {
      template: props.templateId,
      variable_overrides: buildVariableOverrides(),
      status: execStatus,
      context,
    }
    if (scheduleId) {
      execData.schedule_plan = scheduleId
    }
    const execRes = await CreateExecution(execData)

    const exec = execRes.data?.data || execRes.data
    const execId = exec?.id

    if (!execId) {
      throw new Error('Execution creation returned no ID')
    }

    // Determine message based on schedule type
    if (scheduleType.value === 'timed') {
      ElMessage.success({
        message: execStatus === 'pending'
          ? `Execution #${execId} created. Scheduled at ${scheduledDate.value} ${scheduledTime.value}.`
          : `Execution #${execId} created. Schedule set for ${scheduledDate.value} ${scheduledTime.value}. If not approved 30min before, it will auto-cancel.`,
        duration: 6000,
      })
    } else {
      ElMessage.success({
        message: execStatus === 'pending'
          ? `Execution #${execId} created (ready to start).`
          : `Execution #${execId} created (pending_approval). Start it manually after ServiceNow approval.`,
        duration: 6000,
      })
    }

    visible.value = false
    emit('execution-created', execId)
  } catch (e: any) {
    const errMsg = e?.response?.data?.msg || e?.msg || e?.message || 'Submission failed'
    ElMessage.error(errMsg)
  } finally {
    submitting.value = false
  }
}

// ---------- Dialog Lifecycle ----------
function resetWizard() {
  activeStep.value = 0
  validationResult.value = null
  stepError.value = ''
  selectedCr.value = null
  riskResult.value = null
  riskChecked.value = []
  riskConfirmed.value = false
  scheduleType.value = 'manual'
  scheduledDate.value = ''
  scheduledTime.value = ''
}

function handleClose() {
  emit('update:modelValue', false)
}

watch(() => props.modelValue, (val) => {
  if (val) {
    resetWizard()
    loadCrList()
    loadVars()
  }
})
</script>

<style scoped>
.wizard-dialog :deep(.el-dialog__body) {
  padding: 0 24px;
  min-height: 360px;
}

/* Steps */
.wizard-steps {
  padding: 20px 0 0;
}
.wizard-steps :deep(.el-step__title) {
  font-size: 13px;
}
.wizard-steps :deep(.el-step__description) {
  font-size: 11px;
}

/* Body */
.wizard-body {
  min-height: 280px;
}

/* Step Header */
.step-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}
.step-icon {
  font-size: 28px;
  flex-shrink: 0;
}
.step-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}
.step-desc {
  margin: 2px 0 0;
  font-size: 12px;
  color: #909399;
}

/* Step Action */
.step-action {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.action-hint {
  font-size: 12px;
  color: #909399;
}

/* Stats Row */
.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}
.stat-card {
  flex: 1;
  background: #f8f9fa;
  padding: 14px;
  border-radius: 10px;
  text-align: center;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}
.stat-label {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

/* Result Section */
.result-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.result-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 13px;
}
.result-icon {
  font-size: 18px;
  flex-shrink: 0;
}
.result-pass {
  background: #f0f9eb;
}
.result-warn {
  background: #fdf6ec;
}
.result-error {
  background: #fef0f0;
}
.result-title {
  font-weight: 600;
  margin-bottom: 2px;
}
.result-desc {
  color: #666;
  line-height: 1.5;
}
.result-pass .result-title { color: #67C23A; }
.result-warn .result-title { color: #E6A23C; }
.result-error .result-title { color: #F56C6C; }

.suggestion-box {
  background: #f0f5ff;
  border-radius: 8px;
  padding: 12px 14px;
}
.suggestion-title {
  font-weight: 600;
  font-size: 13px;
  color: #409EFF;
  margin-bottom: 6px;
}
.suggestion-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #666;
  line-height: 1.8;
}

/* Step 2: CR */
.cr-selector {
  margin-bottom: 16px;
}
.cr-option {
  padding: 4px 0;
}
.cr-option-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2px;
}
.cr-number {
  font-weight: 700;
  color: #409EFF;
  font-family: monospace;
}
.cr-status {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 8px;
}
.cr-status.approved { background: #f0f9eb; color: #67C23A; }
.cr-status.pending { background: #fdf6ec; color: #E6A23C; }
.cr-option-title {
  font-size: 13px;
  color: #303133;
  margin-bottom: 2px;
}
.cr-option-meta {
  font-size: 11px;
  color: #909399;
  display: flex;
  gap: 12px;
}

.cr-detail-card {
  background: #f8f9fa;
  border-radius: 10px;
  padding: 14px;
}
.cr-detail-row {
  display: flex;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
}
.cr-detail-row:last-child { border-bottom: none; }
.cr-detail-label {
  flex: 0 0 110px;
  color: #909399;
  flex-shrink: 0;
}
.cr-detail-value {
  flex: 1;
  color: #303133;
}
.cr-detail-desc {
  flex-direction: column;
  gap: 4px;
}

/* Step 3: Variables */
.no-vars { padding: 30px 0; }
.vars-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.var-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 8px;
}
.var-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.var-info {
  display: flex;
  align-items: center;
  gap: 6px;
}
.var-key {
  font-family: monospace;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}
.var-type-tag { font-size: 10px; }
.var-desc {
  font-size: 11px;
  color: #c0c4cc;
}

/* Step 4: Risk */
.analysis-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 14px;
}
.card-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 8px;
  color: #303133;
}
.card-body {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
}
.risk-item {
  background: #fff;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 8px;
  border: 1px solid;
}
.risk-high { border-color: #fef0f0; }
.risk-medium { border-color: #fdf6ec; }
.risk-low { border-color: #f0f5ff; }
.risk-item :deep(.el-checkbox__label) { flex: 1; }
.risk-content {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}
.risk-text { padding-top: 1px; }
.suggestion-card {
  background: #f0f5ff;
}
.suggestion-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #666;
  line-height: 1.8;
}
.confirm-bar {
  background: #fef7e0;
  border: 1px solid #fdf6ec;
  border-radius: 8px;
  padding: 12px 14px;
}
.confirm-text {
  font-size: 13px;
  color: #7c6a2b;
}
.step-error { margin-top: 12px; }

/* Step 5: Schedule */
.schedule-option {
  margin-bottom: 20px;
}
.schedule-radios {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}
.schedule-radio-item {
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 14px;
  width: 100%;
  transition: all 0.2s;
}
.schedule-radio-item:has(:checked) {
  border-color: #409EFF;
  background: #ecf5ff;
}
.radio-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.radio-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.radio-desc {
  font-size: 12px;
  color: #909399;
}
.schedule-radio-item :deep(.el-radio__label) {
  width: 100%;
}

.schedule-picker {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.picker-row {
  display: flex;
  gap: 16px;
}
.picker-field {
  flex: 1;
}
.picker-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.window-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #ecf5ff;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 12px;
  color: #409EFF;
}
.cancel-warning {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  background: #fef0f0;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: #F56C6C;
}
.manual-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  background: #ecf5ff;
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 13px;
  color: #409EFF;
}
.manual-hint code {
  background: #d9ecff;
  padding: 1px 6px;
  border-radius: 4px;
  font-family: monospace;
}

/* Footer */
.wizard-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.footer-left, .footer-right {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
