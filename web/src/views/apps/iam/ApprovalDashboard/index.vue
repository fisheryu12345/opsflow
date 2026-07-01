<template>
  <div class="iam-section">
    <div class="iam-section-header">
      <div class="iam-section-header-left">
        <span class="iam-section-title">
          <el-icon size="16"><List /></el-icon>
          {{ $t('message.iam.approval') }}
        </span>
        <span v-if="selectedIds.length" class="iam-batch-count">{{ $t('message.iam.selected', { n: selectedIds.length }) }}</span>
      </div>
      <div class="iam-filter-bar">
        <template v-if="selectedIds.length">
          <el-button size="small" type="success" :icon="Select" :loading="batchLoading" @click="onBatchApprove">
            {{ $t('message.iam.batchApprove') }} ({{ selectedIds.length }})
          </el-button>
          <el-button size="small" type="danger" :icon="Close" :loading="batchLoading" @click="onBatchReject">
            {{ $t('message.iam.batchReject') }} ({{ selectedIds.length }})
          </el-button>
          <el-divider direction="vertical" />
          <el-button size="small" text @click="clearSelection">{{ $t('message.iam.clearSelection') }}</el-button>
        </template>
        <el-select v-model="filterType" :placeholder="$t('message.iam.filterByType')" clearable
          size="small" style="width:130px" @change="fetchPending">
          <el-option :label="$t('message.iam.roleType')" value="role" />
          <el-option :label="$t('message.iam.menuType')" value="menu" />
          <el-option :label="$t('message.iam.buttonType')" value="menu_button" />
          <el-option :label="$t('message.iam.filterPermission')" value="permission" />
          <el-option :label="$t('message.iam.filterProjectRole')" value="project_role" />
        </el-select>
        <el-button size="small" text :icon="Refresh" @click="fetchPending">
          {{ $t('message.iam.refresh') }}
        </el-button>
      </div>
    </div>

    <el-table ref="tableRef" :data="requests" v-loading="loading" size="small" class="iam-table"
      @selection-change="onSelectionChange">
      <el-table-column type="selection" width="40" />
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="user_name" :label="$t('message.iam.applicant')" width="110" />
      <el-table-column :label="$t('message.iam.type')" width="80">
        <template #default="{ row }">
          <el-tag :type="requestTypeTag(row.request_type)" size="small">{{ isEn ? row.request_type_label_en : row.request_type_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.target')" min-width="140">
        <template #default="{ row }">
          {{ row.target_iam_role_name || row.target_role_name || (isEn ? row.target_permission_label_en : row.target_permission_label) || row.target_permission || row.target_menu_name || row.target_project_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="reason" :label="$t('message.iam.reason')" min-width="160" show-overflow-tooltip />
      <el-table-column :label="$t('message.iam.createdAt')" width="150">
        <template #default="{ row }">{{ row.create_datetime }}</template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.actions')" width="160" align="center" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text type="success" @click="onApprove(row)">{{ $t('message.iam.approve') }}</el-button>
          <el-button size="small" text type="danger" @click="onReject(row)">{{ $t('message.iam.reject') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && requests.length === 0" :image-size="60" :description="$t('message.iam.noPending')" />

    <div class="iam-pagination" v-if="total > 0">
      <el-pagination v-model:currentPage="page" :page-size="pageSize" :total="total"
        layout="prev, pager, next, total, sizes" @update:currentPage="fetchPending"
        @update:pageSize="fetchPending" background size="small" />
    </div>

    <!-- Single Review Dialog -->
    <el-dialog v-model="reviewVisible"
      :title="reviewAction === 'approve' ? $t('message.iam.approveRequest') : $t('message.iam.rejectRequest')"
      width="440px" class="opsflow-dialog" destroy-on-close top="12vh" append-to-body>
      <div class="iam-review-info">
        <div class="iam-review-row"><span class="iam-review-label">{{ $t('message.iam.applicant') }}</span>{{ reviewRequest?.user_name }}</div>
        <div class="iam-review-row"><span class="iam-review-label">{{ $t('message.iam.type') }}</span>{{ isEn ? reviewRequest?.request_type_label_en : reviewRequest?.request_type_label }}</div>
        <div class="iam-review-row"><span class="iam-review-label">{{ $t('message.iam.target') }}</span>{{ reviewRequest?.target_role_name || (isEn ? reviewRequest?.target_permission_label_en : reviewRequest?.target_permission_label) || reviewRequest?.target_permission || reviewRequest?.target_menu_name || '-' }}</div>
        <div class="iam-review-row"><span class="iam-review-label">{{ $t('message.iam.reason') }}</span>{{ reviewRequest?.reason }}</div>
      </div>
      <el-form label-width="80px" size="small">
        <el-form-item :label="$t('message.iam.reviewComment')">
          <el-input v-model="reviewComment" type="textarea" :rows="2" :placeholder="$t('message.iam.commentOptional')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="reviewVisible = false">{{ $t('message.iam.cancel') }}</el-button>
        <el-button v-if="reviewAction === 'approve'" size="small" type="success" :loading="reviewLoading" @click="confirmApprove">
          {{ $t('message.iam.confirmApprove') }}
        </el-button>
        <el-button v-if="reviewAction === 'reject'" size="small" type="danger" :loading="reviewLoading" @click="confirmReject">
          {{ $t('message.iam.confirmReject') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Batch Review Dialog -->
    <el-dialog v-model="batchVisible"
      :title="batchAction === 'approve' ? $t('message.iam.batchApprove') : $t('message.iam.batchReject')"
      width="520px" class="opsflow-dialog" destroy-on-close top="10vh" append-to-body>
      <div class="iam-review-info">
        <el-alert :title="$t('message.iam.batchConfirm', { batchAction: batchAction === 'approve' ? $t('message.iam.approve') : $t('message.iam.reject'), n: selectedIds.length })"
          :type="batchAction === 'approve' ? 'success' : 'warning'" :closable="false" show-icon style="margin-bottom:12px;" />
        <div class="iam-batch-list">
          <div v-for="r in selectedRequests" :key="r.id" class="iam-batch-item">
            <span class="iam-batch-id">#{{ r.id }}</span>
            <span class="iam-batch-user">{{ r.user_name }}</span>
            <el-tag size="small" class="iam-batch-tag">{{ isEn ? r.request_type_label_en : r.request_type_label }}</el-tag>
            <span class="iam-batch-target">{{ r.target_role_name || (isEn ? r.target_permission_label_en : r.target_permission_label) || r.target_permission || r.target_menu_name || '-' }}</span>
          </div>
        </div>
      </div>
      <el-form label-width="80px" size="small">
        <el-form-item :label="$t('message.iam.reviewComment')">
          <el-input v-model="batchComment" type="textarea" :rows="2" :placeholder="$t('message.iam.batchCommentHint')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="batchVisible = false">{{ $t('message.iam.cancel') }}</el-button>
        <el-button v-if="batchAction === 'approve'" size="small" type="success" :loading="batchReviewLoading" @click="confirmBatchApprove">
          {{ $t('message.iam.confirmApprove') }} ({{ selectedIds.length }})
        </el-button>
        <el-button v-if="batchAction === 'reject'" size="small" type="danger" :loading="batchReviewLoading" @click="confirmBatchReject">
          {{ $t('message.iam.confirmReject') }} ({{ selectedIds.length }})
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Refresh, List, Select, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { ApproveRequest, RejectRequest } from '/@/api/iam/requests'
import { request } from '/@/utils/service'

const i18n = useI18n()
const t = i18n.t
const isEn = computed(() => String(i18n.locale.value).startsWith('en'))

const requests = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterType = ref<string | null>(null)

// Selection
const tableRef = ref<any>(null)
const selectedRows = ref<any[]>([])
const selectedIds = computed(() => selectedRows.value.map((r: any) => r.id))
const selectedRequests = computed(() => selectedRows.value)

// Single review
const reviewVisible = ref(false)
const reviewAction = ref<'approve' | 'reject'>('approve')
const reviewRequest = ref<any>(null)
const reviewComment = ref('')
const reviewLoading = ref(false)

// Batch review
const batchVisible = ref(false)
const batchAction = ref<'approve' | 'reject'>('approve')
const batchComment = ref('')
const batchReviewLoading = ref(false)
const batchLoading = ref(false)

function requestTypeTag(type: string) {
  const map: Record<string, string> = { role: 'success', menu: 'primary', menu_button: 'warning', permission: 'info', project_role: 'danger' }
  return map[type] || 'info'
}

function onSelectionChange(rows: any[]) { selectedRows.value = rows }

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

async function fetchPending() {
  loading.value = true
  try {
    const params: any = { status: 'pending', page: page.value, limit: pageSize.value }
    if (filterType.value) params.request_type = filterType.value
    const res = await request({ url: '/api/iam/requests/', method: 'get', params })
    requests.value = res.data || []
    total.value = res.total || 0
  } catch { /* ignore */ }
  loading.value = false
}

// ── Single actions ──

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
    ElMessage.success(t('message.iam.approved'))
    await fetchPending()
  } catch (e: any) { ElMessage.error(e?.msg || t('message.iam.errors.approveFailed')) }
  reviewLoading.value = false
}

async function confirmReject() {
  if (!reviewRequest.value) return
  reviewLoading.value = true
  try {
    await RejectRequest(reviewRequest.value.id, { review_comment: reviewComment.value })
    reviewVisible.value = false
    ElMessage.success(t('message.iam.rejected'))
    await fetchPending()
  } catch (e: any) { ElMessage.error(e?.msg || t('message.iam.errors.rejectFailed')) }
  reviewLoading.value = false
}

// ── Batch actions ──

function onBatchApprove() {
  if (!selectedIds.value.length) return
  batchAction.value = 'approve'
  batchComment.value = ''
  batchVisible.value = true
}
function onBatchReject() {
  if (!selectedIds.value.length) return
  batchAction.value = 'reject'
  batchComment.value = ''
  batchVisible.value = true
}

async function confirmBatchApprove() {
  batchReviewLoading.value = true
  let success = 0
  let failed = 0
  for (const id of selectedIds.value) {
    try {
      await ApproveRequest(id, { review_comment: batchComment.value })
      success++
    } catch { failed++ }
  }
  batchReviewLoading.value = false
  batchVisible.value = false
  ElMessage.success(t('message.iam.batchSuccess', { action: t('message.iam.approve'), success, failed }))
  clearSelection()
  await fetchPending()
}

async function confirmBatchReject() {
  batchReviewLoading.value = true
  let success = 0
  let failed = 0
  for (const id of selectedIds.value) {
    try {
      await RejectRequest(id, { review_comment: batchComment.value })
      success++
    } catch { failed++ }
  }
  batchReviewLoading.value = false
  batchVisible.value = false
  ElMessage.success(t('message.iam.batchSuccess', { action: t('message.iam.reject'), success, failed }))
  clearSelection()
  await fetchPending()
}

onMounted(() => fetchPending())
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.iam-section {
  background: $g-bg-card;
  border: 1px solid $g-border-card;
  border-radius: $g-radius-card;
  padding: $g-padding-card;
}
.iam-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.iam-section-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.iam-section-title {
  font-size: 15px;
  font-weight: 600;
  color: $g-text-primary;
  display: flex;
  align-items: center;
  gap: 8px;
  .el-icon { color: $g-color-primary; }
}
.iam-batch-count {
  font-size: 12px;
  color: #409eff;
  background: #ecf5ff;
  padding: 2px 10px;
  border-radius: 10px;
}
.iam-filter-bar {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}
.iam-table { width: 100%; }
.iam-pagination { display: flex; justify-content: flex-end; padding-top: 12px; }
.iam-review-info {
  padding-bottom: 12px;
  font-size: 13px;
  color: $g-text-regular;
}
.iam-review-row {
  padding: 3px 0;
  display: flex;
  gap: 8px;
}
.iam-review-label {
  color: $g-text-muted;
  font-size: 12px;
  min-width: 70px;
}

.iam-batch-list {
  max-height: 280px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 8px;
}
.iam-batch-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  font-size: 13px;
  border-radius: 6px;
  & + & { border-top: 1px solid #f5f5f5; }
  &:hover { background: #fafbfc; }
}
.iam-batch-id { color: #909399; font-family: monospace; font-size: 12px; min-width: 36px; }
.iam-batch-user { font-weight: 500; color: #303133; min-width: 70px; }
.iam-batch-tag { flex-shrink: 0; }
.iam-batch-target { color: #606266; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.opsflow-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.opsflow-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }
</style>
