<template>
  <div class="approval-dashboard">
    <div class="section-header">
      <span class="section-title">
        <el-icon size="16"><List /></el-icon>
        Approval Dashboard
      </span>
      <div class="filter-bar">
        <el-select v-model="filterType" placeholder="All types" clearable style="width: 140px" @change="fetchPending">
          <el-option label="Role" value="role" />
          <el-option label="Menu" value="menu" />
          <el-option label="Button" value="menu_button" />
        </el-select>
        <el-button :icon="Refresh" @click="fetchPending">Refresh</el-button>
      </div>
    </div>

    <el-table :data="requests" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="user_name" label="Applicant" width="120" />
      <el-table-column label="Type" width="90">
        <template #default="{ row }">
          <el-tag :type="requestTypeTag(row.request_type)" size="small">{{ row.request_type_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Target" min-width="160">
        <template #default="{ row }">
          {{ row.target_role_name || row.target_menu_name || row.target_menu_button_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="reason" label="Reason" min-width="200" show-overflow-tooltip />
      <el-table-column label="Created" width="160">
        <template #default="{ row }">{{ row.create_datetime }}</template>
      </el-table-column>
      <el-table-column label="Actions" width="180" fixed="right">
        <template #default="{ row }">
          <el-button type="success" size="small" @click="onApprove(row)">Approve</el-button>
          <el-button type="danger" size="small" @click="onReject(row)">Reject</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap" v-if="total > 0">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                     layout="prev, pager, next, total" @current-change="fetchPending" />
    </div>

    <!-- Review Dialog -->
    <el-dialog v-model="reviewVisible" :title="reviewAction === 'approve' ? 'Approve Request' : 'Reject Request'" width="480px" class="opsflow-dialog">
      <div class="review-info">
        <div class="review-row"><span class="review-label">Applicant:</span> {{ reviewRequest?.user_name }}</div>
        <div class="review-row"><span class="review-label">Type:</span> {{ reviewRequest?.request_type_label }}</div>
        <div class="review-row"><span class="review-label">Target:</span> {{ reviewRequest?.target_role_name || reviewRequest?.target_menu_name || '-' }}</div>
        <div class="review-row"><span class="review-label">Reason:</span> {{ reviewRequest?.reason }}</div>
      </div>
      <el-form label-width="100px" class="review-form">
        <el-form-item label="Comment">
          <el-input v-model="reviewComment" type="textarea" :rows="3" placeholder="Optional review comment" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewVisible = false">Cancel</el-button>
        <el-button v-if="reviewAction === 'approve'" type="success" :loading="reviewLoading" @click="confirmApprove">
          Confirm Approve
        </el-button>
        <el-button v-if="reviewAction === 'reject'" type="danger" :loading="reviewLoading" @click="confirmReject">
          Confirm Reject
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh, List } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetRequests, ApproveRequest, RejectRequest } from '/@/api/iam/requests'

const requests = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterType = ref<string | null>(null)

const reviewVisible = ref(false)
const reviewAction = ref<'approve' | 'reject'>('approve')
const reviewRequest = ref<any>(null)
const reviewComment = ref('')
const reviewLoading = ref(false)

function requestTypeTag(type: string) {
  const map: Record<string, string> = { role: 'success', menu: 'primary', menu_button: 'warning' }
  return map[type] || 'info'
}

async function fetchPending() {
  loading.value = true
  try {
    const params: any = { status: 'pending', page: page.value, limit: pageSize.value }
    if (filterType.value) params.request_type = filterType.value
    const res = await GetRequests(params)
    requests.value = res.data || []
    total.value = res.total || 0
  } catch { /* ignore */ }
  loading.value = false
}

function onApprove(row: any) {
  reviewAction.value = 'approve'
  reviewRequest.value = row
  reviewComment.value = ''
  reviewVisible.value = true
}

function onReject(row: any) {
  reviewAction.value = 'reject'
  reviewRequest.value = row
  reviewComment.value = ''
  reviewVisible.value = true
}

async function confirmApprove() {
  if (!reviewRequest.value) return
  reviewLoading.value = true
  try {
    await ApproveRequest(reviewRequest.value.id, { review_comment: reviewComment.value })
    reviewVisible.value = false
    ElMessage.success('Request approved')
    await fetchPending()
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || 'Failed to approve') }
  reviewLoading.value = false
}

async function confirmReject() {
  if (!reviewRequest.value) return
  reviewLoading.value = true
  try {
    await RejectRequest(reviewRequest.value.id, { review_comment: reviewComment.value })
    reviewVisible.value = false
    ElMessage.success('Request rejected')
    await fetchPending()
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || 'Failed to reject') }
  reviewLoading.value = false
}

onMounted(() => fetchPending())
</script>

<style>
.approval-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title .el-icon {
  color: #409EFF;
}
.filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 12px 0 0;
  flex-shrink: 0;
}
.review-info {
  padding: 0 0 16px;
  font-size: 13px;
}
.review-row {
  padding: 4px 0;
}
.review-label {
  color: #909399;
  display: inline-block;
  width: 80px;
}
.review-form {
  border-top: 1px solid #ebeef5;
  padding-top: 16px;
}
.opsflow-dialog .el-dialog__header {
  padding: 16px 20px;
  margin: 0;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
}
.opsflow-dialog .el-dialog__body {
  padding: 20px;
}
.opsflow-dialog .el-dialog__footer {
  padding: 12px 20px;
  border-top: 1px solid #e4e7ed;
}
</style>
