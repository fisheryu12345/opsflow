<template>
  <div class="app-page">
    <!-- Hero Section -->
    <div class="app-hero">
      <div class="app-hero-bg" />
      <div class="app-hero-inner">
        <div class="app-hero-left">
          <h1 class="app-hero-title">Pending Approvals</h1>
          <p class="app-hero-subtitle">Executions awaiting human review</p>
        </div>
        <div class="app-hero-center">
          <el-input v-model="searchQuery" placeholder="Search by template..." clearable size="default"
            class="app-search-input" @keyup.enter="onSearch" @clear="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="app-hero-stats">
          <div class="app-stat-item"><span class="app-stat-value">{{ total }}</span><span class="app-stat-label">Pending</span></div>
          <div class="app-stat-divider" />
          <div class="app-stat-item"><span class="app-stat-value">{{ urgentCount }}</span><span class="app-stat-label">&gt; 1h</span></div>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="app-body">
      <!-- Filter bar -->
      <div class="app-filter-bar">
        <div class="app-filter-tabs">
          <div class="app-tab" :class="{ active: filterUrgent === '' }" @click="filterUrgent = ''; onSearch()">
            <span class="app-tab-dot" style="background:#409EFF" />All
          </div>
          <div class="app-tab" :class="{ active: filterUrgent === 'urgent' }" @click="filterUrgent = 'urgent'; onSearch()">
            <span class="app-tab-dot" style="background:#F56C6C" />Urgent (&gt;1h)
          </div>
        </div>
        <div class="app-filter-actions">
          <el-button :icon="Refresh" @click="fetchData" :loading="loading" text size="small">Refresh</el-button>
        </div>
      </div>

      <!-- Table card -->
      <div class="app-table-card">
        <el-table :data="displayList" v-loading="loading" stripe style="width:100%" :empty-text="emptyText" size="small">
          <el-table-column prop="template_name" label="Template" min-width="200" show-overflow-tooltip />
          <el-table-column label="Approval Node" width="180">
            <template #default="{ row }">
              <span class="app-node-badge"><el-icon size="12" style="margin-right:4px"><Clock /></el-icon>{{ row.node_id }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Wait Duration" width="130">
            <template #default="{ row }">
              <span class="app-wait" :class="{ 'wait-urgent': isUrgent(row) }">{{ formatWait(row.paused_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="260" fixed="right">
            <template #default="{ row }">
              <div class="app-actions">
                <el-button size="small" type="success" :icon="CircleCheck" @click.stop="handleApprove(row)"
                  :loading="actionLoading === row.id + '-approve'" round>Approve</el-button>
                <el-button size="small" type="danger" :icon="Close" @click.stop="handleReject(row)"
                  :loading="actionLoading === row.id + '-reject'" round>Reject</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
        <div class="app-pagination" v-if="total > 0">
          <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
            layout="prev, pager, next, total" @current-change="fetchData" small />
        </div>
      </div>
    </div>

    <!-- Reject dialog -->
    <el-dialog v-model="rejectVisible" title="Reject Approval" width="420px" top="20vh" destroy-on-close>
      <el-form>
        <el-form-item label="Reason">
          <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="Reason for rejection..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false" size="small">Cancel</el-button>
        <el-button type="danger" @click="confirmReject" size="small">Confirm Reject</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search, CircleCheck, Close, Clock } from '@element-plus/icons-vue'
import { GetPendingApprovals, ApproveNode, RejectNode } from '/@/api/opsflow/executions'

const loading = ref(false)
const actionLoading = ref<string | null>(null)
const list = ref<any[]>([])
const searchQuery = ref('')
const filterUrgent = ref('')
const page = ref(1)
const pageSize = ref(20)

const rejectVisible = ref(false)
const rejectReason = ref('')
const currentRow = ref<any>(null)

const total = computed(() => displayList.value.length)
const urgentCount = computed(() => displayList.value.filter(r => isUrgent(r)).length)
const emptyText = computed(() => loading.value ? 'Loading...' : 'No pending approvals — all caught up!')

const displayList = computed(() => {
  let items = list.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(r => (r.template_name || '').toLowerCase().includes(q))
  }
  if (filterUrgent.value === 'urgent') {
    items = items.filter(r => isUrgent(r))
  }
  return items
})

function formatWait(isoStr: string | null): string {
  if (!isoStr) return '-'
  const paused = new Date(isoStr).getTime()
  const diff = Math.floor((Date.now() - paused) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  return `${Math.floor(diff / 86400)}d`
}

function isUrgent(row: any): boolean {
  if (!row.paused_at) return false
  const diff = Date.now() - new Date(row.paused_at).getTime()
  return diff > 3600000  // > 1h
}

async function fetchData() {
  loading.value = true
  try {
    const res = await GetPendingApprovals()
    list.value = res.data?.data || res.data?.results || res.data || []
  } catch { list.value = [] }
  loading.value = false
}

async function handleApprove(row: any) {
  actionLoading.value = row.id + '-approve'
  try {
    await ApproveNode(row.id, row.node_id, 'Approved from dashboard')
    ElMessage.success(`Approved execution #${row.id}`)
    await fetchData()
  } catch (e: any) { ElMessage.error(e?.msg || 'Approve failed') }
  actionLoading.value = null
}

function handleReject(row: any) {
  currentRow.value = row; rejectReason.value = ''; rejectVisible.value = true
}

async function confirmReject() {
  if (!currentRow.value) return
  actionLoading.value = currentRow.value.id + '-reject'
  try {
    await RejectNode(currentRow.value.id, currentRow.value.node_id, rejectReason.value || 'Rejected from dashboard')
    ElMessage.success(`Rejected execution #${currentRow.value.id}`)
    rejectVisible.value = false; await fetchData()
  } catch (e: any) { ElMessage.error(e?.msg || 'Reject failed') }
  actionLoading.value = null
}

function onSearch() { page.value = 1 }

onMounted(fetchData)
</script>

<style scoped>
.app-page { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; background: #f5f6fa; overflow: hidden; }

/* ===== Hero ===== */
.app-hero { position: relative; flex-shrink: 0; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.app-hero-bg { position: absolute; inset: 0; opacity: 0.06; background-image: radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 30%, #fff 1px, transparent 1px); background-size: 40px 40px; }
.app-hero-inner { position: relative; z-index: 1; padding: 12px 20px; display: flex; flex-direction: row; align-items: center; gap: 16px; }
.app-hero-left { flex: 0 0 auto; }
.app-hero-title { margin: 0; font-size: 22px; font-weight: 800; color: #fff; white-space: nowrap; }
.app-hero-subtitle { margin: 0; font-size: 11px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.app-hero-center { flex: 1 1 auto; min-width: 0; }
.app-search-input { width: 100%; max-width: 320px; }
.app-search-input :deep(.el-input__wrapper) { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.12); box-shadow: none; border-radius: 10px; padding: 2px 12px; }
.app-search-input :deep(.el-input__inner) { color: #fff; font-size: 14px; }
.app-search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
.app-search-input :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
.app-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.app-stat-item { text-align: center; padding: 0 14px; }
.app-stat-value { display: block; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.2; }
.app-stat-label { font-size: 10px; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.5px; }
.app-stat-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.1); }

/* ===== Body ===== */
.app-body { flex: 1; overflow-y: auto; padding: 0 16px 24px; }

/* ===== Filter bar ===== */
.app-filter-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa; }
.app-filter-tabs { display: flex; gap: 4px; }
.app-tab { display: flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266; cursor: pointer; transition: all 0.2s; user-select: none; }
.app-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.app-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.app-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.app-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ===== Table card ===== */
.app-table-card { background: #fff; border-radius: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.06); overflow: hidden; }
.app-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.app-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.app-node-badge { display: inline-flex; align-items: center; font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 8px; background: #fdf6ec; color: #E6A23C; }
.app-wait { font-family: 'SF Mono', monospace; font-size: 12px; color: #909399; }
.app-wait.wait-urgent { color: #F56C6C; font-weight: 600; }
.app-actions { display: flex; gap: 6px; }
.app-pagination { display: flex; justify-content: flex-end; padding: 12px 16px; }
</style>
