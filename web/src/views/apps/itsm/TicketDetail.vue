<template>
  <div class="ticket-detail" v-loading="loading">
    <div class="td-header">
      <div class="td-header-top">
        <div class="td-card-title">{{ $t('message.ticketDetail.ticketInfo') }}</div>
        <div class="td-header-actions">
          <el-button text @click="goBack">
            <el-icon><ArrowLeft /></el-icon> {{ $t('message.common.back') }}
          </el-button>
          <el-button text @click="loadTicket" :loading="loading">
            <el-icon><Refresh /></el-icon> {{ $t('message.itsmPage.refresh') }}
          </el-button>
        </div>
      </div>
      <div class="td-header-row" v-if="ticket">
        <span class="td-sn">{{ ticket.sn }}</span>
        <span class="td-status-badge" :class="'it-status-' + (ticket.current_status || '')">
          <span class="td-status-dot" />{{ statusLabel(ticket.current_status) }}
        </span>
        <span class="td-prio-badge" :class="'it-prio-' + (ticket.priority || 'p3').toLowerCase()">
          {{ ticket.priority }}
        </span>
        <span class="td-meta-divider" />
        <b>{{ ticket.title }}</b>
        <span class="td-meta-divider" />
        <span>{{ ticket.itsm_type }}</span>
        <span class="td-meta-divider" />
        <span>{{ $t('message.itsmPage.colCreator') }}: {{ ticket.creator_name || ticket.creator || '-' }}</span>
        <span class="td-meta-divider" />
        <span>{{ ticket.create_datetime || '' }}</span>
      </div>
    </div>

    <!-- SLA 信息卡片 -->
    <div class="td-sla-card" :class="'sla-' + ticket.sla_info.sla_status" v-if="ticket?.sla_info">
      <div class="td-card-title">{{ $t('message.ticketDetail.slaInfo') }}</div>
      <div class="td-sla-grid">
        <div class="td-sla-item">
          <span class="td-sla-label">{{ $t('message.ticketDetail.slaStatus') }}</span>
          <span :class="'sla-badge sla-' + ticket.sla_info.sla_status">
            {{ slaStatusLabel(ticket.sla_info.sla_status) }}
          </span>
        </div>
        <div class="td-sla-item">
          <span class="td-sla-label">{{ $t('message.ticketDetail.slaPolicy') }}</span>
          <span>{{ ticket.sla_info.policy_name || '-' }}</span>
        </div>
        <div class="td-sla-item">
          <span class="td-sla-label">{{ $t('message.ticketDetail.slaRemaining') }}</span>
          <span :style="{ color: ticket.sla_info.remaining_seconds < 300 ? '#F56C6C' : '#67C23A' }">
            {{ formatSlaTime(ticket.sla_info.remaining_seconds) }}
          </span>
        </div>
        <div class="td-sla-item">
          <span class="td-sla-label">{{ $t('message.ticketDetail.slaReplyDeadline') }}</span>
          <span>{{ ticket.sla_info.reply_deadline ? ticket.sla_info.reply_deadline.slice(0,16).replace('T', ' ') : '-' }}</span>
        </div>
        <div class="td-sla-item">
          <span class="td-sla-label">{{ $t('message.ticketDetail.slaResolveDeadline') }}</span>
          <span>{{ ticket.sla_info.deadline ? ticket.sla_info.deadline.slice(0,16).replace('T', ' ') : '-' }}</span>
        </div>
      </div>
    </div>

    <div class="td-body">
      <div class="td-summary-card" v-if="summaryNode">
        <div class="td-card-title">{{ $t('message.ticketDetail.ticketContent') }}</div>
        <div class="td-summary-grid">
          <div v-for="(val, key) in summaryNode.fields_data" :key="key" class="td-summary-cell">
            <span class="td-summary-label">{{ submittedFieldLabels[key] || key }}</span>
            <span class="td-summary-value">{{ String(val) }}</span>
          </div>
        </div>
      </div>

      <div class="td-steps-card" v-if="(flowStates && Object.keys(flowStates).length) || (pipelineTree?.nodes?.length)">
        <div class="td-card-title td-collapse-title" @click="onToggleFlow">
          <el-icon><component :is="flowCollapsed ? 'ArrowRight' : 'ArrowDown'" /></el-icon>
          {{ $t('message.ticketDetail.flowSteps') }}
        </div>
        <div v-show="!flowCollapsed">
          <FlowChart ref="flowChartRef" :pipeline-tree="pipelineTree" :node-status="ticketNodeStatus" />
        </div>
      </div>

      <!-- Draft mode: allow edit + resubmit -->
      <div class="td-action-card" v-if="ticket?.current_status === 'draft' && summaryNode">
        <div class="td-card-title">重新提交</div>
        <div class="td-action-body">
          <ItsmFormRenderer
            mode="fill"
            :fields="summaryNode.fields || []"
            :data="fillForm"
            :submitting="submitting"
            :submit-text="'重新提交'"
            @field-change="(k, v) => fillForm[k] = v"
            @submit="onResubmit"
          />
        </div>
      </div>

      <div class="td-action-card" v-else-if="currentNode">
        <div class="td-card-title">{{ $t('message.ticketDetail.currentNode') }} · {{ currentNode.name }}</div>
        <div class="td-action-body">
          <template v-if="currentNode.type === 'APPROVAL' || currentNode.type === 'SIGN'">
            <div class="td-processor">
              <el-icon><User /></el-icon> {{ $t('message.ticketDetail.processor') }}: {{ currentNode.processor_name || currentNode.processors }}
            </div>
            <ItsmFormRenderer
              v-if="(currentNode.fields || []).length"
              mode="fill"
              :fields="currentNode.fields || []"
              :data="fillForm"
              :submitting="submitting"
              :show-submit="false"
              @field-change="(k, v) => fillForm[k] = v"
            />
            <template v-if="isProcessor(currentNode.processors)">
              <div class="td-approval-btns">
                <el-button type="success" :loading="submitting" @click="onApprove">
                  <el-icon><Select /></el-icon> {{ $t('message.ticketDetail.approveBtn') }}
                </el-button>
                <el-button type="danger" :loading="submitting" @click="onReject">
                  <el-icon><Close /></el-icon> {{ $t('message.ticketDetail.rejectBtn') }}
                </el-button>
              </div>
            </template>
            <div v-else class="td-action-placeholder">
              <p>{{ currentNode.name }}（{{ stepTypeLabel(currentNode.type) }}）</p>
              <p style="font-size:12px;color:#E6A23C">您不是当前节点处理人，无法操作</p>
            </div>
          </template>

          <template v-else-if="currentNode.type === 'NORMAL'">
            <ItsmFormRenderer
              mode="fill"
              :fields="currentNode.fields || []"
              :data="fillForm"
              :submitting="submitting"
              @field-change="(k, v) => fillForm[k] = v"
              @submit="onNodeSubmit"
            />
          </template>

          <div v-else class="td-action-placeholder">
            {{ currentNode.name }}（{{ stepTypeLabel(currentNode.type) }}）
          </div>
        </div>
      </div>

      <div class="td-timeline-card" v-if="finishedNodes.length">
        <div class="td-card-title">{{ $t('message.ticketDetail.finishedNodes') }}</div>
        <div class="td-timeline">
          <div v-for="(ns, idx) in finishedNodes" :key="ns.id" class="td-timeline-item">
            <div class="td-timeline-col">
              <div class="td-timeline-dot td-dot-finished" />
              <div v-if="idx < finishedNodes.length - 1" class="td-timeline-line" />
            </div>
            <div class="td-timeline-content">
              <div class="td-timeline-name">{{ ns.name }}</div>
              <div class="td-timeline-meta">
                <span>{{ ns.processor_name || '-' }}</span>
                <span v-if="ns.finish_time"> · {{ formatTime(ns.finish_time) }}</span>
              </div>
              <div v-if="ns.result_label || ns.result_comment" class="td-timeline-result">
                <el-tag v-if="ns.result_label" size="small" :type="ns.result_val === 'passed' ? 'success' : 'danger'">{{ ns.result_label }}</el-tag>
                <span v-if="ns.result_comment" class="td-timeline-comment">{{ ns.result_comment }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, ArrowDown, User, Select, Close, Refresh } from '@element-plus/icons-vue'
import FlowChart from './FlowChart.vue'
import ItsmFormRenderer from '/@/components/ItsmFormRenderer/index.vue'
import { ticketApi, GetTicketStatus, NodeSubmit, SubmitTicket, ApproveTicketNode, RejectTicketNode, workflowVersionApi } from '/@/api/itsm/index'
import { useUserInfo } from '/@/stores/userInfo'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const userInfo = useUserInfo()

function getMyUserId(): number | null {
  const raw = sessionStorage.getItem('userInfo') || localStorage.getItem('userInfo')
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      return parsed.id || parsed.userId || null
    } catch {}
  }
  return userInfo.userInfos.id || null
}

function isProcessor(processors: string): boolean {
  const userId = getMyUserId()
  if (!userId || !processors) {
    return false
  }
  try {
    const arr = JSON.parse(processors)
    if (Array.isArray(arr)) return arr.some((u: any) => parseInt(u) === userId)
  } catch {}
  return parseInt(processors) === userId
}

const loading = ref(false)
const submitting = ref(false)
const flowCollapsed = ref(true)
const flowChartRef = ref<any>(null)

function onToggleFlow() {
  flowCollapsed.value = !flowCollapsed.value
  if (!flowCollapsed.value) {
    nextTick(() => { flowChartRef.value?.buildGraph?.() })
  }
}
const ticket = ref<any>(null)
const ticketNodeStatus = ref<any[]>([])
const ticketSignTasks = ref<Record<number, any>>({})
const fillForm = reactive<Record<string, any>>({})

const flowSteps = ref<any[]>([])
const currentNode = ref<any>(null)
const finishedNodes = ref<any[]>([])
const submittedFieldLabels = ref<Record<string, string>>({})
const flowStates = ref<Record<string, any>>({})
const pipelineTree = ref<{ nodes: any[]; edges: any[] } | null>(null)

const summaryNode = computed(() =>
  finishedNodes.value.find(n => n.type === 'NORMAL' && n.fields_data && Object.keys(n.fields_data).length > 0) || null
)

function goBack() {
  sessionStorage.setItem('itsm_active_tab', 'tickets')
  router.back()
}

function statusLabel(s: string) {
  const m: Record<string, string> = {
    draft: '草稿', assigned: '已分派', receiving: '待认领',
    running: '处理中', suspended: '挂起', finished: '已完成',
    terminated: '已终止', failed: '失败',
  }
  return m[s] || s || '未知'
}

function stepTypeLabel(t: string) {
  const m: Record<string, string> = {
    NORMAL: '填单', APPROVAL: '审批', SIGN: '会签',
    TASK: '自动任务', START: '开始', END: '结束',
  }
  return m[t] || t || ''
}

function formatTime(dt: string | undefined | null): string {
  if (!dt) return ''
  return dt.replace(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}).*$/, '$1')
}

function slaStatusLabel(s: string): string {
  const m: Record<string, string> = {
    normal: t('message.itsmPage.slaNormal'),
    warning: t('message.itsmPage.slaWarning'),
    violated: t('message.itsmPage.slaViolated'),
  }
  return m[s] || s || ''
}

function formatSlaTime(seconds: number | null | undefined): string {
  if (seconds == null || seconds <= 0) return t('message.itsmPage.slaViolated')
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const hr = t('message.itsmPage.slaHours')
  const mi = t('message.itsmPage.slaMinutes')
  if (h > 0) return `${h} ${hr} ${m} ${mi}`
  return `${m} ${mi}`
}

async function loadTicket() {
  const id = route.params.id as string
  if (!id) return
  loading.value = true
  try {
    // Parallelize independent calls
    const [res, statusRes] = await Promise.all([
      ticketApi.detail(id),
      GetTicketStatus(id),
    ])
    ticket.value = res?.data || res
    const statusData = statusRes?.data || statusRes
    ticketNodeStatus.value = statusData?.node_status || []

    const stMap: Record<number, any> = {}
    for (const st of (statusData?.sign_tasks || [])) {
      const sid = st.status || st.status_id
      if (sid && !stMap[sid]) stMap[sid] = st
    }
    ticketSignTasks.value = stMap

    const wfVersionId = ticket.value?.workflow_version
    let allStates: Record<string, any> = {}
    if (wfVersionId) {
      const wfRes = await workflowVersionApi.detail(String(wfVersionId))
      const wfData = wfRes?.data || wfRes
      allStates = wfData?.states || {}
      flowStates.value = allStates
      pipelineTree.value = wfData?.pipeline_tree || null
    }

    rebuildFlow(allStates)
    // Pre-fill from previous submission when draft
    if (ticket.value?.current_status === 'draft') {
      const firstFill = ticketNodeStatus.value.find((n: any) => n.type === 'NORMAL' && n.fields && Object.keys(n.fields).length)
      if (firstFill) Object.assign(fillForm, firstFill.fields)
    }
  } catch {
    ElMessage.error(t('message.ticketDetail.loadFailed'))
  }
  loading.value = false
}

function rebuildFlow(allStates: Record<string, any>) {
  const steps: any[] = []
  const done: any[] = []
  const seenIds = new Set<number>()

  const statusByStateId: Record<string, any> = {}
  for (const ns of ticketNodeStatus.value) {
    statusByStateId[String(ns.state_id || ns.id)] = ns
  }

  const labels: Record<string, string> = {}

  for (const [key, state] of Object.entries(allStates)) {
    const st = state as any
    if (seenIds.has(st.id)) continue
    seenIds.add(st.id)
    const ns = statusByStateId[String(st.id)] || statusByStateId[key]
    const status = ns?.status || 'WAIT'
    const signTask = ticketSignTasks.value[ns?.id]
    const step = {
      id: st.id,
      key,
      name: st.name,
      type: st.type,
      status,
      processors: ns?.processors || '',
      processor_name: ns?.processor_name || signTask?.processor || (st.type === 'NORMAL' && ticket.value ? (ticket.value.creator_name || String(ticket.value.creator)) : '') || '',
      fields: st.fields || [],
      fields_data: ns?.fields || {},
      finish_time: ns?.update_datetime || '',
      result_val: signTask?.status_val || '',
      result_label: signTask?.status_val === 'passed' ? t('message.ticketDetail.approveSuccess') : signTask?.status_val === 'rejected' ? t('message.ticketDetail.rejectSuccess') : '',
      result_comment: signTask?.comment || '',
    }
    if (status === 'RUNNING') {
      // Handled below via runningSteps filtering
    } else if (status === 'FINISHED') {
      done.push(step)
    }
    steps.push(step)

    for (const f of (st.fields || [])) {
      labels[String(f.key)] = f.name || f.key
    }
  }

  submittedFieldLabels.value = labels
  flowSteps.value = steps
  finishedNodes.value = done

  // With parallel gateways, multiple nodes may be RUNNING.
  // Prefer the one where current user is a processor, then fall back to last.
  const runningSteps = steps.filter((s: any) => s.status === 'RUNNING')
  if (runningSteps.length > 0) {
    const mine = runningSteps.find((s: any) => isProcessor(s.processors))
    currentNode.value = mine || runningSteps[runningSteps.length - 1]
  } else {
    currentNode.value = null
  }
}

async function onResubmit(data?: Record<string, any>) {
  if (!ticket.value || submitting.value) return
  const fields: Record<string, any> = {}
  const source = data || fillForm
  for (const [k, v] of Object.entries(source)) {
    if (v != null && v !== '') fields[k] = v
  }
  submitting.value = true
  try {
    // Save only form_data (merge into existing meta), then submit
    await ticketApi.update(String(ticket.value.id), {
      meta: { ...(ticket.value?.meta || {}), form_data: fields },
    } as any)
    await SubmitTicket(ticket.value.id)
    ElMessage.success('重新提交成功')
    router.back()
  } catch (e: any) { ElMessage.error(e?.msg || '提交失败') }
  submitting.value = false
}

function collectFillFields(): Record<string, any> {
  const fields: Record<string, any> = {}
  for (const [k, v] of Object.entries(fillForm)) {
    if (v != null && v !== '') fields[k] = v
  }
  return fields
}

async function onApprove() {
  if (!ticket.value || !currentNode.value) return
  submitting.value = true
  try {
    const fields = collectFillFields()
    await ApproveTicketNode(ticket.value.id, currentNode.value.state_id || currentNode.value.id, '', fields)
    ElMessage.success(t('message.ticketDetail.approveSuccess'))
    router.back()
  } catch (e: any) { ElMessage.error(e?.msg || t('message.ticketDetail.approveFailed')) }
  submitting.value = false
}

async function onReject() {
  if (!ticket.value || !currentNode.value) return
  const fields = collectFillFields()
  const hasComment = Object.values(fields).some(v => v && String(v).trim())
  if (!hasComment) {
    ElMessage.warning(t('message.ticketDetail.rejectReason'))
    return
  }
  submitting.value = true
  try {
    const fields = collectFillFields()
    await RejectTicketNode(ticket.value.id, currentNode.value.state_id || currentNode.value.id, '', fields)
    ElMessage.success(t('message.ticketDetail.rejectSuccess'))
    router.back()
  } catch (e: any) { ElMessage.error(e?.msg || t('message.ticketDetail.rejectFailed')) }
  submitting.value = false
}

async function onNodeSubmit(formData?: Record<string, any>) {
  if (submitting.value || !ticket.value || !currentNode.value) return
  const stateId = currentNode.value.state_id || currentNode.value.id
  const source = formData || fillForm
  const fields: Record<string, any> = {}
  for (const [k, v] of Object.entries(source)) {
    if (v != null && v !== '') fields[k] = v
  }
  submitting.value = true
  try {
    await NodeSubmit(ticket.value.id, { state_id: stateId, fields })
    ElMessage.success(t('message.ticketDetail.submitSuccess'))
    router.back()
  } catch (e: any) { ElMessage.error(e?.msg || t('message.ticketDetail.submitFailed')) }
  submitting.value = false
}

onMounted(() => loadTicket())
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.ticket-detail { padding: 16px 24px 40px; }
.td-header { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); padding: 16px 24px; margin-bottom: 16px; }
.td-header-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.td-back-btn { font-size: 13px; color: #606266; .el-icon { font-size: 14px; margin-right: 2px; } }
.td-header-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; font-size: 13px; color: #606266; line-height: 1.6; }
.td-sn { font-size: 17px; font-weight: 700; color: #1d2129; font-family: 'SF Mono', Consolas, monospace; letter-spacing: 0.3px; }
.td-status-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px; }
.td-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.it-status-running .td-status-dot { background: #409EFF; }
.it-status-running { background: #ecf5ff; color: #409EFF; }
.it-status-draft .td-status-dot { background: #c0c4cc; }
.it-status-draft { background: #f5f7fa; color: #909399; }
.it-status-finished .td-status-dot { background: #67C23A; }
.it-status-finished { background: #f0f9eb; color: #67C23A; }
.it-status-suspended .td-status-dot { background: #E6A23C; }
.it-status-suspended { background: #fdf6ec; color: #E6A23C; }
.it-status-terminated .td-status-dot { background: #F56C6C; }
.it-status-terminated { background: #fef0f0; color: #F56C6C; }
.td-prio-badge { font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 10px; }
.it-prio-p1 { background: #fef0f0; color: #F56C6C; }
.it-prio-p2 { background: #fdf6ec; color: #E6A23C; }
.it-prio-p3, .it-prio-p4 { background: #f0f9eb; color: #67C23A; }
.td-meta-divider { width: 1px; height: 14px; background: #dcdfe6; flex-shrink: 0; }
.td-body { display: flex; flex-direction: column; gap: 16px; }
.td-card-title { font-size: 15px; font-weight: 600; color: #1d2129; margin-bottom: 12px; }
.td-collapse-title { cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px; }
.td-collapse-title:hover { color: #409EFF; }

.td-sla-card { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); padding: 18px 24px; margin-bottom: 16px; border-left: 4px solid #909399; }
.td-sla-card.sla-violated { border-left-color: #F56C6C; }
.td-sla-card.sla-warning { border-left-color: #E6A23C; }
.td-sla-grid { display: flex; flex-wrap: wrap; gap: 12px; }
.td-sla-item { display: flex; flex-direction: column; gap: 2px; min-width: 120px; }
.td-sla-label { font-size: 11px; color: #909399; }
.sla-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 8px; }
.sla-normal { background: #f0f9eb; color: #67C23A; }
.sla-warning { background: #fdf6ec; color: #E6A23C; }
.sla-violated { background: #fef0f0; color: #F56C6C; }

.td-summary-card { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); padding: 18px 24px; border-left: 4px solid #67C23A; }
.td-summary-grid { display: flex; flex-wrap: wrap; }
.td-summary-cell { width: 50%; display: flex; align-items: center; gap: 8px; padding: 5px 0; font-size: 13px; }
.td-summary-label { color: #86909c; font-weight: 500; flex-shrink: 0; min-width: 70px; }
.td-summary-value { color: #1d2129; word-break: break-all; }

.td-steps-card { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); padding: 16px 24px; overflow: hidden; }
.td-action-card { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); padding: 18px 24px; border-left: 4px solid #409EFF; }
.td-action-body { min-height: 40px; }
.td-processor { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #606266; margin-bottom: 14px; }
.td-approval-btns { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; .el-button { min-width: 100px; } }
.td-action-placeholder { color: #909399; font-size: 13px; }

.td-timeline-card { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); padding: 18px 24px; }
.td-timeline { display: flex; flex-direction: column; gap: 0; }
.td-timeline-item { display: flex; align-items: flex-start; gap: 14px; padding: 0; position: relative; }
.td-timeline-col { display: flex; flex-direction: column; align-items: center; width: 18px; flex-shrink: 0; }
.td-timeline-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 10px; flex-shrink: 0; z-index: 1; }
.td-timeline-line { width: 2px; flex: 1; min-height: 28px; background: #e8e8e8; }
.td-dot-finished { background: #67C23A; }
.td-timeline-content { flex: 1; padding: 8px 0 18px; border-bottom: 1px solid #f0f0f0; }
.td-timeline-item:last-child .td-timeline-content { border-bottom: none; }
.td-timeline-name { font-size: 14px; font-weight: 500; color: #1d2129; }
.td-timeline-meta { font-size: 12px; color: #86909c; margin-top: 3px; }
.td-timeline-result { margin-top: 4px; display: flex; align-items: center; gap: 6px; }
.td-timeline-comment { font-size: 12px; color: #606266; }
</style>
