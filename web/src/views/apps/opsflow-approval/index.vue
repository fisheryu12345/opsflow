<template>
  <div class="approval-page">
    <div class="ap-body">
      <!-- Header -->
      <div class="ap-header">
        <div class="ap-header-left">
          <div class="ap-title-row">
            <div class="ap-title-icon">
              <el-icon :size="18" color="#fff"><CircleCheck /></el-icon>
            </div>
            <div>
              <h2 class="ap-title">Pending Approvals</h2>
              <span class="ap-subtitle">Executions awaiting human review</span>
            </div>
          </div>
        </div>
        <div class="ap-header-right">
          <el-button :icon="Refresh" @click="fetchData" :loading="loading" round>Refresh</el-button>
        </div>
      </div>

      <!-- Approval list -->
      <div class="ap-card">
        <el-table :data="list" v-loading="loading" stripe style="width:100%" empty-text="No pending approvals">
          <el-table-column label="#" width="50">
            <template #default="{ $index }">{{ $index + 1 }}</template>
          </el-table-column>
          <el-table-column prop="template_name" label="Template" min-width="160" show-overflow-tooltip />
          <el-table-column prop="node_id" label="Approval Node" width="160">
            <template #default="{ row }">
              <el-tag type="warning" effect="dark" size="small">
                <el-icon size="12" style="margin-right:2px"><Clock /></el-icon>
                {{ row.node_id }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Wait Duration" width="140">
            <template #default="{ row }">
              <span class="wait-time">{{ formatWait(row.paused_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="280" fixed="right">
            <template #default="{ row }">
              <div class="ap-actions">
                <el-button size="small" type="success" @click="handleApprove(row)"
                  :loading="actionLoading === row.id + '-approve'">
                  <el-icon><CircleCheck /></el-icon> Approve
                </el-button>
                <el-button size="small" type="danger" @click="handleReject(row)"
                  :loading="actionLoading === row.id + '-reject'">
                  <el-icon><Close /></el-icon> Reject
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Reject dialog -->
    <el-dialog v-model="rejectVisible" title="Reject Approval" width="420px">
      <el-form>
        <el-form-item label="Reason">
          <el-input v-model="rejectReason" type="textarea" :rows="3"
            placeholder="Reason for rejection..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">Cancel</el-button>
        <el-button type="danger" @click="confirmReject">Confirm Reject</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, CircleCheck, Close, Clock } from '@element-plus/icons-vue'
import { GetPendingApprovals, ApproveNode, RejectNode } from '/@/api/opsflow/executions'

const loading = ref(false)
const actionLoading = ref<string | null>(null)
const list = ref<any[]>([])
const rejectVisible = ref(false)
const rejectReason = ref('')
const currentRow = ref<any>(null)

function formatWait(isoStr: string | null): string {
  if (!isoStr) return '-'
  const paused = new Date(isoStr).getTime()
  const now = Date.now()
  const diff = Math.floor((now - paused) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  return `${Math.floor(diff / 86400)}d`
}

async function fetchData() {
  loading.value = true
  try {
    const res = await GetPendingApprovals()
    list.value = res.data?.data || res.data?.results || res.data || []
  } catch {
    list.value = []
  }
  loading.value = false
}

async function handleApprove(row: any) {
  actionLoading.value = row.id + '-approve'
  try {
    await ApproveNode(row.id, row.node_id, 'Approved from dashboard')
    ElMessage.success(`Approved execution #${row.id}`)
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Approve failed')
  }
  actionLoading.value = null
}

function handleReject(row: any) {
  currentRow.value = row
  rejectReason.value = ''
  rejectVisible.value = true
}

async function confirmReject() {
  if (!currentRow.value) return
  actionLoading.value = currentRow.value.id + '-reject'
  try {
    await RejectNode(currentRow.value.id, currentRow.value.node_id, rejectReason.value || 'Rejected from dashboard')
    ElMessage.success(`Rejected execution #${currentRow.value.id}`)
    rejectVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Reject failed')
  }
  actionLoading.value = null
}

onMounted(fetchData)
</script>

<style scoped>
.approval-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #eef1f5 100%);
  overflow: hidden;
}
.ap-body {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 16px;
}
.ap-header {
  display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;
}
.ap-title-row { display: flex; align-items: center; gap: 14px; }
.ap-title-icon {
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, #9B59B6, #8E44AD);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(155,89,182,0.30);
}
.ap-title { margin: 0; font-size: 22px; font-weight: 700; color: #1a1a2e; }
.ap-subtitle { font-size: 13px; color: #909399; }
.ap-header-right { display: flex; gap: 12px; align-items: center; }
.ap-card {
  background: rgba(255,255,255,0.90);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  padding: 16px;
  border: 1px solid rgba(255,255,255,0.6);
}
.ap-actions { display: flex; gap: 6px; }
.wait-time { font-family: monospace; font-size: 12px; color: #909399; }
</style>
