<template>
  <el-dialog
    v-model="visible"
    title="Submit Execution Wizard"
    width="960px"
    top="3vh"
    :close-on-click-modal="false"
    class="opsflow-dialog exec-wizard"
    @close="handleClose"
  >
    <!-- Step Progress -->
    <div class="wiz-header">
      <div class="wiz-steps" data-tour="wizard-steps">
        <div
          v-for="(step, i) in steps"
          :key="i"
          class="wiz-step"
          :class="{ active: activeStep === i, done: activeStep > i }"
        >
          <div class="wiz-step-indicator">
            <span v-if="activeStep > i" class="wiz-step-check">✓</span>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <div class="wiz-step-label">
            <div class="wiz-step-title">{{ step.title }}</div>
            <div class="wiz-step-desc">{{ step.desc }}</div>
          </div>
          <div v-if="i < steps.length - 1" class="wiz-step-connector" :class="{ done: activeStep > i }" />
        </div>
      </div>
      <div class="wiz-progress">
        <div class="wiz-progress-bar" :style="{ width: `${((activeStep + 1) / steps.length) * 100}%` }" />
      </div>
    </div>

    <div class="wiz-body" v-loading="stepLoading">
      <!-- ==================== Step 1: Validation ==================== -->
      <div v-show="activeStep === 0" class="wiz-step-panel">
        <div class="panel-hero">
          <div class="panel-hero-icon">🔍</div>
          <div class="panel-hero-text">
            <h3>Pipeline Validation</h3>
            <p>Validate topology, node configuration, and engine compatibility</p>
          </div>
        </div>

        <div class="metric-row">
          <div class="metric-card">
            <div class="metric-value">{{ pipelineNodes.length }}</div>
            <div class="metric-label">Nodes</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ pipelineEdges.length }}</div>
            <div class="metric-label">Edges</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ atomTypesCount }}</div>
            <div class="metric-label">Atom Types</div>
          </div>
        </div>

        <div v-if="!validationResult" class="wiz-action">
          <el-button
            type="primary"
            size="large"
            :loading="stepLoading"
            @click="runValidation"
            :icon="Search"
            class="wiz-action-btn"
          >
            Run Validation
          </el-button>
          <span class="wiz-action-hint">AI analyzes pipeline structure for compliance</span>
        </div>

        <transition name="panel-fade">
          <div v-if="validationResult" class="result-block">
            <div v-if="!validationResult.hasErrors" class="result-hero result-hero-pass">
              <div class="result-hero-icon">✓</div>
              <div class="result-hero-text">
                <div class="result-hero-title">Validation Passed</div>
                <div class="result-hero-desc">Topology is complete, no orphan nodes, gateway paths correct, Bamboo engine compatible</div>
              </div>
            </div>

            <div v-for="(w, i) in validationResult.warnings" :key="'w'+i" class="result-item result-item-warn">
              <span class="result-item-icon">⚠</span>
              <div class="result-item-body">
                <span class="result-item-title">Warning</span>
                <span class="result-item-desc">{{ w }}</span>
              </div>
            </div>

            <div v-for="(e, i) in validationResult.errors" :key="'e'+i" class="result-item result-item-error">
              <span class="result-item-icon">✕</span>
              <div class="result-item-body">
                <span class="result-item-title">Error</span>
                <span class="result-item-desc">{{ e }}</span>
              </div>
            </div>

            <div v-if="validationResult.suggestions?.length" class="suggest-block">
              <div class="suggest-header">💡 Suggestions</div>
              <ul class="suggest-list">
                <li v-for="(s, i) in validationResult.suggestions" :key="i">{{ s }}</li>
              </ul>
            </div>
          </div>
        </transition>
      </div>

      <!-- ==================== Step 2: Change Request ==================== -->
      <div v-show="activeStep === 1" class="wiz-step-panel">
        <div class="panel-hero">
          <div class="panel-hero-icon">📋</div>
          <div class="panel-hero-text">
            <h3>Link Change Request</h3>
            <p>Select the change request associated with this pipeline</p>
          </div>
        </div>

        <div class="cr-selector" v-loading="crLoading">
          <el-select
            v-model="selectedCr"
            placeholder="Search change requests..."
            filterable
            value-key="cr_number"
            style="width:100%"
            size="large"
            @change="onCrChange"
          >
            <el-option
              v-for="cr in crList"
              :key="cr.cr_number"
              :label="`${cr.cr_number} - ${cr.title}`"
              :value="cr"
            >
              <div class="cr-opt">
                <div class="cr-opt-head">
                  <span class="cr-opt-number">{{ cr.cr_number }}</span>
                  <el-tag
                    :type="cr.status === 'approved' ? 'success' : 'warning'"
                    size="small"
                    effect="plain"
                  >
                    {{ cr.status === 'approved' ? 'Approved' : 'Pending' }}
                  </el-tag>
                </div>
                <div class="cr-opt-title">{{ cr.title }}</div>
                <div class="cr-opt-meta">
                  <span>{{ cr.requester }}</span>
                  <span>{{ cr.change_window_start }} ~ {{ cr.change_window_end }}</span>
                </div>
              </div>
            </el-option>
          </el-select>
        </div>

        <transition name="panel-fade">
          <div v-if="selectedCr" class="info-card">
            <div class="info-card-header">Change Request Details</div>
            <div class="info-card-grid">
              <div class="info-field">
                <span class="info-label">CR Number</span>
                <span class="info-value mono">{{ selectedCr.cr_number }}</span>
              </div>
              <div class="info-field">
                <span class="info-label">Title</span>
                <span class="info-value">{{ selectedCr.title }}</span>
              </div>
              <div class="info-field">
                <span class="info-label">Status</span>
                <span class="info-value">
                  <el-tag
                    :type="selectedCr.status === 'approved' ? 'success' : 'warning'"
                    size="small"
                  >
                    {{ selectedCr.status === 'approved' ? 'Approved' : 'Pending' }}
                  </el-tag>
                </span>
              </div>
              <div class="info-field">
                <span class="info-label">Change Window</span>
                <span class="info-value">{{ selectedCr.change_window_start }} ~ {{ selectedCr.change_window_end }}</span>
              </div>
              <div class="info-field">
                <span class="info-label">Requester</span>
                <span class="info-value">{{ selectedCr.requester }}</span>
              </div>
              <div class="info-field info-field-full">
                <div class="info-desc-label">Description</div>
                <div class="info-desc-value">{{ selectedCr.description }}</div>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <!-- ==================== Step 3: Parameters ==================== -->
      <div v-show="activeStep === 2" class="wiz-step-panel">
        <div class="panel-hero">
          <div class="panel-hero-icon">⚙️</div>
          <div class="panel-hero-text">
            <h3>Parameters &amp; Variables</h3>
            <p>Override template variable defaults for this execution</p>
          </div>
        </div>

        <div v-if="templateVarsKeys.length === 0" class="wiz-empty">
          <el-empty description="No parameters defined in this template" :image-size="48" />
        </div>
        <div v-else class="var-list">
          <div v-for="key in templateVarsKeys" :key="key" class="var-item">
            <div class="var-item-head">
              <div class="var-item-info">
                <span class="var-item-key">{{ key }}</span>
                <el-tag size="small" effect="plain" class="var-item-tag">{{ varTypeLabel(templateVars[key]?.type) }}</el-tag>
              </div>
              <span v-if="templateVars[key]?.description" class="var-item-desc">{{ templateVars[key].description }}</span>
            </div>
            <el-input
              v-model="overrides[key]"
              :type="inputType(templateVars[key]?.type)"
              :rows="templateVars[key]?.type === 'textarea' ? 3 : 1"
              :placeholder="defaultPlaceholder(templateVars[key])"
              size="default"
            />
          </div>
        </div>
      </div>

      <!-- ==================== Step 4: Risk Analysis ==================== -->
      <div v-show="activeStep === 3" class="wiz-step-panel">
        <div class="panel-hero">
          <div class="panel-hero-icon">🛡️</div>
          <div class="panel-hero-text">
            <h3>AI Risk Analysis &amp; Confirmation</h3>
            <p>Review change impact and acknowledge each risk item</p>
          </div>
        </div>

        <div v-if="!riskResult" class="wiz-action">
          <el-button
            type="warning"
            size="large"
            :loading="riskLoading"
            @click="runRiskAnalysis"
            :icon="Aim"
            class="wiz-action-btn"
          >
            Execute Risk Analysis
          </el-button>
          <span class="wiz-action-hint">AI analyzes change impact and identifies risks</span>
        </div>

        <transition name="panel-fade">
          <div v-if="riskResult" class="risk-block">
            <div class="risk-section">
              <div class="risk-section-icon">📋</div>
              <div class="risk-section-title">Change Summary</div>
              <p class="risk-section-body">{{ riskResult.summary }}</p>
            </div>

            <div v-if="riskResult.risks?.length" class="risk-section">
              <div class="risk-section-icon">⚠️</div>
              <div class="risk-section-title">Risk Items — acknowledge each to proceed</div>
              <div
                v-for="(risk, i) in riskResult.risks"
                :key="i"
                class="risk-card"
                :class="'risk-card-' + (risk.level || 'low')"
              >
                <el-checkbox v-model="riskChecked[i]" @change="onRiskCheckChange">
                  <div class="risk-card-content">
                    <span class="risk-card-badge" :class="'badge-' + (risk.level || 'low')">
                      {{ risk.level === 'high' ? 'High' : risk.level === 'medium' ? 'Medium' : 'Low' }}
                    </span>
                    <span class="risk-card-text">{{ risk.text }}</span>
                  </div>
                </el-checkbox>
              </div>
            </div>

            <div v-if="riskResult.suggestions?.length" class="risk-section risk-section-suggest">
              <div class="risk-section-icon">💡</div>
              <div class="risk-section-title">Suggestions</div>
              <ul class="suggest-list">
                <li v-for="(s, i) in riskResult.suggestions" :key="i">{{ s }}</li>
              </ul>
            </div>

            <div class="risk-confirm">
              <el-checkbox v-model="riskConfirmed">
                <span class="risk-confirm-text">
                  <strong>I acknowledge all risks above</strong> and confirm this execution. I assume responsibility for any unlisted risks.
                </span>
              </el-checkbox>
            </div>
          </div>
        </transition>

        <div v-if="stepError" class="wiz-error">
          <el-alert :title="stepError" type="error" show-icon :closable="false" />
        </div>
      </div>

      <!-- ==================== Step 5: Schedule ==================== -->
      <div v-show="activeStep === 4" class="wiz-step-panel">
        <div class="panel-hero">
          <div class="panel-hero-icon">⏰</div>
          <div class="panel-hero-text">
            <h3>Schedule Strategy</h3>
            <p>Set execution timing after approval</p>
          </div>
        </div>

        <div class="mode-selector">
          <div
            class="mode-card"
            :class="{ active: scheduleType === 'timed' }"
            @click="scheduleType = 'timed'"
          >
            <div class="mode-card-icon">⏱️</div>
            <div class="mode-card-content">
              <div class="mode-card-title">Scheduled Execution</div>
              <div class="mode-card-desc">Auto-execute at a specified time after approval</div>
            </div>
            <div class="mode-card-radio" :class="{ checked: scheduleType === 'timed' }" />
          </div>
          <div
            class="mode-card"
            :class="{ active: scheduleType === 'manual' }"
            @click="scheduleType = 'manual'"
          >
            <div class="mode-card-icon">👆</div>
            <div class="mode-card-content">
              <div class="mode-card-title">Manual Trigger</div>
              <div class="mode-card-desc">Manually start after ServiceNow approval completes</div>
            </div>
            <div class="mode-card-radio" :class="{ checked: scheduleType === 'manual' }" />
          </div>
        </div>

        <transition name="panel-fade">
          <div v-if="scheduleType === 'timed'" class="schedule-card">
            <div class="schedule-card-header">
              <el-icon size="16" color="#409EFF"><Calendar /></el-icon>
              <span>Pick Execution Time</span>
            </div>
            <div class="schedule-pickers">
              <div class="schedule-field">
                <label class="schedule-label">Date</label>
                <el-date-picker
                  v-model="scheduledDate"
                  type="date"
                  placeholder="Select date"
                  :disabled-date="disabledDate"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                />
              </div>
              <div class="schedule-field">
                <label class="schedule-label">Time</label>
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

            <div v-if="selectedCr" class="schedule-info schedule-info-blue">
              <el-icon><InfoFilled /></el-icon>
              <span>Change window: <strong>{{ selectedCr.change_window_start }}</strong> ~ <strong>{{ selectedCr.change_window_end }}</strong> · Available: <strong>{{ windowStart }}</strong> ~ <strong>{{ windowEndExclusive }}</strong></span>
            </div>

            <div class="schedule-info schedule-info-red">
              <el-icon><WarningFilled /></el-icon>
              <span>If not approved <strong>30 minutes</strong> before the scheduled time, this plan <strong>auto-cancels</strong>. Ensure timely approval.</span>
            </div>
          </div>

          <div v-else class="manual-card">
            <div class="manual-card-body">
              <el-icon size="22" color="#409EFF"><InfoFilled /></el-icon>
              <div class="manual-card-text">
                <div class="manual-card-title">Manual Execution</div>
                <div class="manual-card-desc">
                  Creates an Execution with status <code>pending_approval</code>. After ServiceNow approves the change, you can manually start it from the Executions page.
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <div class="wiz-footer">
        <div class="wiz-footer-left">
          <el-button v-if="activeStep > 0" text size="default" @click="prevStep">
            ← Back
          </el-button>
        </div>
        <div class="wiz-footer-right">
          <el-button plain size="default" @click="visible = false">Cancel</el-button>
          <el-button
            v-if="activeStep < 4"
            type="primary"
            size="default"
            :disabled="!canNext"
            @click="nextStep"
            class="wiz-next-btn"
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
            class="wiz-submit-btn"
          >
            <el-icon><CircleCheck /></el-icon> Submit Execution
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Aim, CircleCheck, InfoFilled, WarningFilled, Calendar } from '@element-plus/icons-vue'
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

const steps = [
  { title: 'Validation', desc: 'Pipeline Check' },
  { title: 'Change', desc: 'Link Change Request' },
  { title: 'Params', desc: 'Variables' },
  { title: 'Risk', desc: 'AI Analysis & Confirm' },
  { title: 'Schedule', desc: 'Timing Strategy' },
]

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
    const raw = res.data?.data || res.data
    // Normalize risks: LLM may return strings or objects — convert to {level, text} format
    if (raw?.risks?.length) {
      raw.risks = raw.risks.map((r: any) =>
        typeof r === 'string' ? { level: 'medium', text: r } : r
      )
    }
    riskResult.value = raw
    riskChecked.value = (raw?.risks || []).map(() => false)
    riskConfirmed.value = false
  } catch (e: any) {
    stepError.value = e?.msg || e?.message || 'Risk analysis failed'
  } finally {
    riskLoading.value = false
  }
}

function onRiskCheckChange() {
  // reactively recomputes canNext
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
  if (activeStep.value === 1 && !crList.value.length) loadCrList()
  if (activeStep.value === 2 && !templateVarsKeys.value.length) loadVars()
  if (activeStep.value < 4) activeStep.value++
}

function prevStep() {
  if (activeStep.value > 0) activeStep.value--
}

// ---------- Submit ----------
function buildVariableOverrides(): Record<string, any> {
  const vars: Record<string, any> = {}
  for (const key of templateVarsKeys.value) {
    const ov = overrides.value[key]
    const def = templateVars.value[key]?.value
    if (ov !== undefined && ov !== null && ov !== def) vars[key] = ov
  }
  return vars
}

async function handleSubmit() {
  if (!props.templateId) return
  submitting.value = true
  try {
    const context: Record<string, any> = {}
    if (selectedCr.value) {
      context.cr_number = selectedCr.value.cr_number
      context.cr_title = selectedCr.value.title
      context.cr_status = selectedCr.value.status
    }
    context.risk_confirmed = riskConfirmed.value
    context.pipeline_validated = !!validationResult.value

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

    const execStatus = selectedCr.value?.status === 'approved' ? 'pending' : 'pending_approval'

    const execData: Record<string, any> = {
      template: props.templateId,
      variable_overrides: buildVariableOverrides(),
      status: execStatus,
      context,
    }
    if (scheduleId) execData.schedule_plan = scheduleId
    const execRes = await CreateExecution(execData)

    const exec = execRes.data?.data || execRes.data
    const execId = exec?.id
    if (!execId) throw new Error('Execution creation returned no ID')

    if (scheduleType.value === 'timed') {
      ElMessage.success({
        message: execStatus === 'pending'
          ? `Execution #${execId} created. Scheduled at ${scheduledDate.value} ${scheduledTime.value}.`
          : `Execution #${execId} created. Schedule set for ${scheduledDate.value} ${scheduledTime.value}. Auto-cancels if not approved 30min before.`,
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

<style lang="scss" scoped>
@import '../styles/opsflow-global';

$accent: #409EFF;
$accent-dark: #337ecc;
$bg-card: #f8f9fb;
$border-light: #e4e7ed;

/* ===== Layout ===== */
.exec-wizard :deep(.el-dialog__body) {
  padding: 0 !important;
  min-height: 400px;
}
.exec-wizard :deep(.el-dialog__footer) {
  padding: 14px 24px;
}

/* ===== Step Header ===== */
.wiz-header {
  padding: 24px 24px 0;
}
.wiz-steps {
  display: flex;
  align-items: flex-start;
  margin-bottom: 16px;
}
.wiz-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  position: relative;
  flex: 1;
}
.wiz-step-indicator {
  width: 28px;
  height: 28px;
  min-width: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  background: $bg-card;
  color: $of-text-muted;
  border: 2px solid #e0e0e0;
  transition: all 0.3s;
}
.wiz-step.active .wiz-step-indicator {
  background: $accent;
  color: #fff;
  border-color: $accent;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.35);
}
.wiz-step.done .wiz-step-indicator {
  background: #67C23A;
  color: #fff;
  border-color: #67C23A;
}
.wiz-step-check {
  font-size: 14px;
}
.wiz-step-label {
  flex: 1;
  min-width: 0;
  padding-top: 3px;
}
.wiz-step-title {
  font-size: 13px;
  font-weight: 600;
  color: $of-text-muted;
  transition: color 0.3s;
}
.wiz-step.active .wiz-step-title {
  color: $accent;
}
.wiz-step.done .wiz-step-title {
  color: #67C23A;
}
.wiz-step-desc {
  font-size: 10px;
  color: #c0c4cc;
  margin-top: 1px;
}
.wiz-step-connector {
  flex: 1;
  height: 2px;
  background: #e8e8e8;
  margin: 13px 12px 0;
  min-width: 12px;
  transition: background 0.3s;
}
.wiz-step-connector.done {
  background: #67C23A;
}
.wiz-progress {
  height: 3px;
  background: #f0f0f0;
  border-radius: 2px;
  margin-bottom: 0;
  overflow: hidden;
}
.wiz-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, $accent, #67C23A);
  border-radius: 2px;
  transition: width 0.4s ease;
}

/* ===== Body ===== */
.wiz-body {
  padding: 20px 24px;
  min-height: 280px;
}
.wiz-step-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ===== Panel Hero ===== */
.panel-hero {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.panel-hero-icon {
  width: 42px;
  height: 42px;
  min-width: 42px;
  border-radius: 12px;
  background: linear-gradient(135deg, #ecf5ff, #f0f8ff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.08);
}
.panel-hero-text h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: $of-text-primary;
  line-height: 1.3;
}
.panel-hero-text p {
  margin: 3px 0 0;
  font-size: 12px;
  color: $of-text-muted;
  line-height: 1.4;
}

/* ===== Action ===== */
.wiz-action {
  display: flex;
  align-items: center;
  gap: 14px;
  background: linear-gradient(135deg, #f8f9fb, #f0f5ff);
  border: 1px dashed #d9ecff;
  border-radius: 12px;
  padding: 20px 24px;
}
.wiz-action-btn {
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.25);
}
.wiz-action-hint {
  font-size: 12px;
  color: #909399;
}

/* ===== Metric Cards ===== */
.metric-row {
  display: flex;
  gap: 14px;
}
.metric-card {
  flex: 1;
  background: #fff;
  border: 1px solid $of-border-card;
  border-radius: 12px;
  padding: 18px 14px;
  text-align: center;
  transition: all 0.25s;
}
.metric-card:hover {
  border-color: $accent;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.08);
  transform: translateY(-2px);
}
.metric-value {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, $accent, $accent-dark);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.metric-label {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ===== Validation Results ===== */
.result-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.result-hero {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 12px;
  border: 1px solid;
}
.result-hero-pass {
  background: linear-gradient(135deg, #f0f9eb, #f4fcf0);
  border-color: #e1f3d8;
}
.result-hero-icon {
  width: 36px;
  height: 36px;
  min-width: 36px;
  border-radius: 50%;
  background: #67C23A;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
}
.result-hero-title {
  font-weight: 700;
  font-size: 15px;
  color: #67C23A;
  margin-bottom: 3px;
}
.result-hero-desc {
  font-size: 13px;
  color: #555;
  line-height: 1.5;
}
.result-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 13px;
  border: 1px solid transparent;
}
.result-item-warn { background: $of-bg-warning; border-color: #faecd8; }
.result-item-error { background: $of-bg-danger; border-color: #fde2e2; }
.result-item-icon { font-size: 15px; flex-shrink: 0; margin-top: 1px; }
.result-item-warn .result-item-icon { color: #E6A23C; }
.result-item-error .result-item-icon { color: #F56C6C; }
.result-item-body { display: flex; align-items: baseline; gap: 6px; min-width: 0; }
.result-item-title { font-weight: 600; flex-shrink: 0; }
.result-item-desc { color: #666; line-height: 1.5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.result-item-warn .result-item-title { color: #E6A23C; }
.result-item-error .result-item-title { color: #F56C6C; }

.suggest-block {
  background: linear-gradient(135deg, #f0f5ff, #f8fbff);
  border: 1px solid #d9ecff;
  border-radius: 10px;
  padding: 14px 16px;
}
.suggest-header {
  font-weight: 600;
  font-size: 13px;
  color: $accent;
  margin-bottom: 6px;
}
.suggest-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #555;
  line-height: 1.8;
}

/* ===== CR Selector ===== */
.cr-selector { margin-bottom: 4px; }
.cr-opt { padding: 4px 0; }
.cr-opt-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3px;
}
.cr-opt-number {
  font-weight: 700;
  color: $accent;
  font-family: monospace;
  font-size: 13px;
}
.cr-opt-title {
  font-size: 13px;
  color: $of-text-primary;
  margin-bottom: 2px;
}
.cr-opt-meta {
  font-size: 11px;
  color: #909399;
  display: flex;
  gap: 14px;
}

/* ===== Info Card ===== */
.info-card {
  background: #fff;
  border: 1px solid $of-border-card;
  border-radius: 12px;
  overflow: hidden;
}
.info-card-header {
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: $of-text-muted;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  background: $bg-card;
  border-bottom: 1px solid $of-border-card;
}
.info-card-grid {
  padding: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}
.info-field {
  width: 50%;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}
.info-field:nth-child(-n+2) { border-top: none; }
.info-field-full { width: 100%; flex-direction: column; display: flex; }
.info-label {
  display: block;
  font-size: 11px;
  color: #909399;
  margin-bottom: 2px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.info-value {
  font-size: 13px;
  color: $of-text-primary;
}
.info-value.mono { font-family: monospace; }
.info-desc-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.info-desc-value {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
}

/* ===== Variables ===== */
.wiz-empty { padding: 20px 0; }
.var-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.var-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid $of-border-card;
  border-radius: 10px;
  transition: all 0.2s;
}
.var-item:hover {
  border-color: #c6e2ff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.06);
}
.var-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.var-item-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.var-item-key {
  font-family: monospace;
  font-size: 14px;
  font-weight: 600;
  color: $of-text-primary;
}
.var-item-tag { font-size: 10px; }
.var-item-desc {
  font-size: 11px;
  color: #c0c4cc;
}

/* ===== Risk ===== */
.risk-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.risk-section {
  background: #fff;
  border: 1px solid $of-border-card;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.risk-section-icon {
  width: 28px;
  height: 28px;
  min-width: 28px;
  border-radius: 8px;
  background: $bg-card;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}
.risk-section-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: $of-text-primary;
  line-height: 28px;
}
.risk-section-body {
  width: 100%;
  margin: 4px 0 0 36px;
  font-size: 13px;
  color: #555;
  line-height: 1.6;
}
.risk-section-suggest {
  background: linear-gradient(135deg, #f0f5ff, #f8fbff);
  border-color: #d9ecff;
}
.risk-card {
  width: 100%;
  margin-left: 36px;
  background: #fafafa;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 4px;
  border: 1px solid #e8eaed;
  transition: all 0.2s;
}
.risk-card:hover {
  transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.risk-card-high { border-left: 3px solid #F56C6C; }
.risk-card-medium { border-left: 3px solid #E6A23C; }
.risk-card-low { border-left: 3px solid #909399; }
.risk-card :deep(.el-checkbox__label) { flex: 1; }
.risk-card-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: #555;
  line-height: 1.5;
}
.risk-card-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
  flex-shrink: 0;
  margin-top: 1px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.badge-high { background: #fef0f0; color: #F56C6C; }
.badge-medium { background: #fdf6ec; color: #E6A23C; }
.badge-low { background: #f0f5ff; color: #909399; }
.risk-card-text { padding-top: 1px; }

.risk-confirm {
  background: linear-gradient(135deg, #fef7e0, #fffdf5);
  border: 1px solid #f5e7b4;
  border-radius: 10px;
  padding: 14px 16px;
}
.risk-confirm-text {
  font-size: 13px;
  color: #7c6a2b;
  line-height: 1.5;
}
.wiz-error { margin-top: 8px; }

/* ===== Schedule ===== */
.mode-selector {
  display: flex;
  gap: 14px;
}
.mode-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: #fff;
  border: 1.5px solid #e8e8e8;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s;
}
.mode-card:hover {
  border-color: #c6e2ff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.06);
}
.mode-card.active {
  border-color: $accent;
  background: linear-gradient(135deg, #ecf5ff, #f5f9ff);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.1);
}
.mode-card-icon {
  font-size: 30px;
  flex-shrink: 0;
}
.mode-card-content {
  flex: 1;
}
.mode-card-title {
  font-size: 15px;
  font-weight: 600;
  color: $of-text-primary;
  margin-bottom: 2px;
}
.mode-card-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
.mode-card-radio {
  width: 20px;
  height: 20px;
  min-width: 20px;
  border-radius: 50%;
  border: 2px solid #d0d0d0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s;
}
.mode-card-radio.checked {
  border-color: $accent;
  background: $accent;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15);
}
.mode-card-radio.checked::after {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
}

/* Schedule card */
.schedule-card {
  background: #fff;
  border: 1px solid $of-border-card;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.schedule-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  padding-bottom: 14px;
  border-bottom: 1px solid #ebeef5;
}
.schedule-pickers {
  display: flex;
  gap: 20px;
}
.schedule-field {
  flex: 1;
}
.schedule-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #909399;
  margin-bottom: 6px;
}
.schedule-info {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  border: 1px solid;
}
.schedule-info-blue {
  background: #ecf5ff;
  border-color: #d9ecff;
  color: $accent;
}
.schedule-info-red {
  background: #fef4f4;
  border-color: #fde2e2;
  color: #c45656;
}
.schedule-info-red .el-icon { color: #F56C6C; }
.schedule-info strong { font-weight: 600; }

/* Manual card */
.manual-card {
  background: linear-gradient(135deg, #fff, #f0f5ff);
  border: 1px solid #d9ecff;
  border-radius: 12px;
  padding: 24px;
}
.manual-card-body {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.manual-card-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.manual-card-title {
  font-size: 15px;
  font-weight: 600;
  color: $of-text-primary;
}
.manual-card-desc {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
}
.manual-card-desc code {
  background: #d9ecff;
  padding: 1px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
}

/* ===== Footer ===== */
.wiz-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.wiz-footer-left, .wiz-footer-right {
  display: flex;
  gap: 10px;
  align-items: center;
}
.wiz-next-btn {
  background: linear-gradient(135deg, $accent, $accent-dark);
  border: none;
}
.wiz-next-btn:hover {
  background: linear-gradient(135deg, #60b0ff, $accent);
}
.wiz-submit-btn {
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
}
.wiz-submit-btn:hover {
  filter: brightness(1.1);
}

/* ===== Transitions ===== */
.panel-fade-enter-active {
  transition: all 0.35s ease;
}
.panel-fade-leave-active {
  transition: all 0.2s ease;
}
.panel-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.panel-fade-leave-to {
  opacity: 0;
}
</style>
