<template>
  <div>
    <!-- Filter bar -->
    <div class="itsm-filter-bar">
      <div class="itsm-filter-tabs">
        <div class="itsm-tab" :class="{ active: ticketFilter === '' }" @click="ticketFilter = ''; loadTickets()">
          <span class="itsm-tab-dot" style="background:#409EFF" />{{ $t('message.itsmPage.filterAll') }}
        </div>
        <div class="itsm-tab" :class="{ active: ticketFilter === 'draft' }" @click="ticketFilter = 'draft'; loadTickets()">
          <span class="itsm-tab-dot" style="background:#E6A23C" />{{ $t('message.itsmPage.filterDraft') }}
        </div>
        <div class="itsm-tab" :class="{ active: ticketFilter === 'running' }" @click="ticketFilter = 'running'; loadTickets()">
          <span class="itsm-tab-dot" style="background:#409EFF" />{{ $t('message.itsmPage.filterRunning') }}
        </div>
        <div class="itsm-tab" :class="{ active: ticketFilter === 'finished' }" @click="ticketFilter = 'finished'; loadTickets()">
          <span class="itsm-tab-dot" style="background:#67C23A" />{{ $t('message.itsmPage.filterFinished') }}
        </div>
      </div>
      <div class="itsm-filter-actions">
        <el-button :icon="Refresh" size="small" text @click="loadTickets" :loading="loading">{{ $t('message.itsmPage.refresh') }}</el-button>
      </div>
    </div>

    <div class="itsm-table-card">
      <el-table :data="tickets" v-loading="loading" stripe style="width:100%" size="small"
        :empty-text="loading ? $t('message.itsmPage.loading') : $t('message.itsmPage.noTickets')">
        <el-table-column prop="sn" :label="$t('message.itsmPage.colSn')" width="160" />
        <el-table-column prop="title" :label="$t('message.itsmPage.colTitle')" min-width="200" show-overflow-tooltip />
        <el-table-column :label="$t('message.itsmPage.colType')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.itsm_type === 'incident' ? 'danger' : row.itsm_type === 'change' ? 'warning' : ''" size="small">
              {{ row.itsm_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colStatus')" width="100">
          <template #default="{ row }">
            <span class="itsm-status-badge" :class="'it-status-' + row.current_status">
              <span class="itsm-status-dot" />{{ statusLabel(row.current_status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colSla')" width="100">
          <template #default="{ row }">
            <span v-if="row.sla_info" :class="'sla-badge sla-' + row.sla_info.sla_status">
              {{ row.sla_info.remaining_seconds != null ? formatSla(row.sla_info.remaining_seconds) : '-' }}
            </span>
            <span v-else style="font-size:12px;color:#C0C4CC">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="priority" :label="$t('message.ticketCreate.priority')" width="80">
          <template #default="{ row }">
            <span class="itsm-prio-badge" :class="'it-prio-' + (row.priority || 'p3').toLowerCase()">{{ row.priority }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colCreator')" width="120">
          <template #default="{ row }">
            {{ row.creator_name || row.creator || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="create_datetime" :label="$t('message.itsmPage.colCreateTime')" width="170" />
        <el-table-column :label="$t('message.itsmPage.colAssignee')" width="140">
          <template #default="{ row }">
            <template v-if="row.meta?.assignee">
              <span style="font-size:13px;color:#606266">{{ row.meta.assignee.name }}</span>
              <el-tag v-if="row.meta.assignee.group" size="small" style="margin-left:4px">{{ row.meta.assignee.group }}</el-tag>
            </template>
            <span v-else-if="row.meta?.assign_group" style="font-size:12px;color:#909399">
              组: {{ row.meta.assign_group.name }}
            </span>
            <span v-else style="font-size:12px;color:#C0C4CC">{{ $t('message.itsmPage.pendingAssignee') }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colActions')" width="280" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.current_status === 'draft'" size="small" text v-can="'itsm:ticket:create'" @click="onSubmitTicket(row)">
              <el-icon><Select /></el-icon> {{ $t('message.itsmPage.submit') }}
            </el-button>
            <el-button size="small" text @click="onViewTicket(row)">
              <el-icon><Search /></el-icon> {{ $t('message.itsmPage.detail') }}
            </el-button>
            <el-button v-if="row.meta?.assignee && row.current_status !== 'finished' && row.current_status !== 'terminated'" size="small" text type="warning" v-can="'itsm:ticket:assign'" @click="ticketAssign(row)">
              <el-icon><User /></el-icon> {{ $t('message.itsmPage.transfer') }}
            </el-button>
            <el-button v-else-if="!row.meta?.assignee && row.current_status !== 'finished' && row.current_status !== 'terminated'" size="small" text type="primary" v-can="'itsm:ticket:assign'" @click="ticketAssign(row)">
              <el-icon><User /></el-icon> {{ $t('message.itsmPage.assign') }}
            </el-button>
            <el-button v-if="row.current_status === 'running'" size="small" text type="danger" v-can="'itsm:ticket:close'" @click="onCloseTicket(row)">
              <el-icon><CircleClose /></el-icon> {{ $t('message.itsmPage.close') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Assign dialog -->
    <el-dialog v-model="assignVisible" :title="$t('message.assignment.title')" width="380px" top="25vh" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="$t('message.assignment.selectUser')">
          <el-select v-model="assignUserId" filterable size="small" style="width:100%"
            :loading="usersLoading" :placeholder="$t('message.assignment.searchUser')">
            <el-option v-for="u in userOptions" :key="u.id" :label="`${u.name} (${u.username})`" :value="u.id" />
          </el-select>
        </el-form-item>
        <div v-if="assignTicketRow" style="font-size:12px;color:#909399;margin-top:-8px;margin-bottom:8px">
          {{ $t('message.assignment.ticketPrefix') }}: <b>{{ assignTicketRow.sn }} - {{ assignTicketRow.title }}</b>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" :disabled="!assignUserId" @click="confirmAssignTicket">{{ $t('message.assignment.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Select, Search, User, CircleClose } from '@element-plus/icons-vue'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { ticketApi, SubmitTicket, CloseTicket, AssignTicket } from '/@/api/itsm/index'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const emit = defineEmits<{ viewTicket: [row: any]; designer: [wfId: number] }>()
const { t } = useI18n()
const router = useRouter()
const { reportStats: updateHeroStats } = useHeroConsumer()

const loading = ref(false)
const tickets = ref<any[]>([])
const ticketFilter = ref('')

// Assign dialog
const assignVisible = ref(false)
const assignUserId = ref<number | null>(null)
const assignTicketRow = ref<any>(null)
const userOptions = ref<any[]>([])
const usersLoading = ref(false)

function statusLabel(s: string) {
  const m: Record<string, string> = {
    draft: t('message.itsmPage.statusDraft'),
    assigned: t('message.itsmPage.statusAssigned'),
    receiving: t('message.itsmPage.statusReceiving'),
    running: t('message.itsmPage.statusRunning'),
    escalated: t('message.itsmPage.statusEscalated'),
    suspended: t('message.itsmPage.statusSuspended'),
    finished: t('message.itsmPage.statusFinished'),
    terminated: t('message.itsmPage.statusTerminated'),
    failed: t('message.itsmPage.statusFailed'),
    success: '成功', firing: '触发中', acknowledged: '已确认', resolved: '已恢复',
  }
  return m[s] || s || t('message.common.empty') || ''
}

function formatSla(seconds: number): string {
  if (seconds <= 0) return t('message.itsmPage.slaOverdue')
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const hr = t('message.itsmPage.slaHours')
  const mi = t('message.itsmPage.slaMinutes')
  if (h > 0) return `${h}${hr}${m}${mi}`
  return `${m}${mi}`
}

async function loadTickets() {
  loading.value = true
  try {
    const params: any = {}
    if (ticketFilter.value) params.current_status = ticketFilter.value
    const res = await ticketApi.list(params)
    tickets.value = res?.results || res?.data || res || []
    reportStats()
  } finally { loading.value = false }
}

function reportStats() {
  updateHeroStats([
    { value: tickets.value.length, label: '工单总数' },
    { value: tickets.value.filter((t: any) => t.current_status === 'running').length, label: '处理中' },
    { value: tickets.value.filter((t: any) => t.current_status === 'draft').length, label: '草稿' },
    { value: tickets.value.filter((t: any) => t.current_status === 'finished').length, label: '已完成' },
  ])
}

// ---- Assign ----
async function loadAllUsers() {
  usersLoading.value = true
  try {
    const { request } = await import('/@/utils/service')
    const res = await request({ url: '/api/iam/users/search/', method: 'get', params: { page_size: 10000 } })
    userOptions.value = ((res as any).data || []).map((item: any) => ({
      id: item.value,
      name: item.label,
    }))
  } catch { userOptions.value = [] }
  usersLoading.value = false
}

async function ticketAssign(row: any) {
  assignTicketRow.value = row
  assignUserId.value = null
  if (!userOptions.value.length) await loadAllUsers()
  assignVisible.value = true
}

async function confirmAssignTicket() {
  if (!assignTicketRow.value || !assignUserId.value) return
  try {
    await AssignTicket(assignTicketRow.value.id, assignUserId.value)
    ElMessage.success('工单已分派')
    assignVisible.value = false
    assignTicketRow.value = null
    assignUserId.value = null
    await loadTickets()
  } catch { ElMessage.error('分派失败') }
}

async function onSubmitTicket(row: any) {
  if (!row?.id) { ElMessage.error('无效工单'); return }
  try {
    await SubmitTicket(row.id)
    ElMessage.success('工单已提交，pipeline 已启动')
    await loadTickets()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || '提交失败')
  }
}

function onViewTicket(row: any) {
  if (row?.id) router.push('/apps/itsm/ticket/' + row.id)
}

async function onCloseTicket(row: any) {
  try {
    await CloseTicket(row.id)
    ElMessage.success('工单已关闭')
    await loadTickets()
  } catch (e: any) {
    ElMessage.error(e?.msg || '关闭失败')
  }
}

onMounted(() => {
  if (props.active) loadTickets()
})

watch(() => props.active, (isActive) => {
  if (isActive && tickets.value.length === 0) loadTickets()
})
</script>
