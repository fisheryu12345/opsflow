<template>
  <div class="iam-section">
    <div class="iam-section-header">
      <span class="iam-section-title">
        <el-icon size="16"><List /></el-icon>
        {{ $t('message.iam.approval') }}
      </span>
      <div class="iam-filter-bar">
        <el-select v-model="filterType" :placeholder="$t('message.iam.allTypes')" clearable
          size="small" style="width:130px" @change="fetchPending">
          <el-option :label="$t('message.iam.roleType')" value="role" />
          <el-option :label="$t('message.iam.menuType')" value="menu" />
          <el-option :label="$t('message.iam.buttonType')" value="menu_button" />
        </el-select>
        <el-button size="small" text :icon="Refresh" @click="fetchPending">
          {{ $t('message.iam.refresh') }}
        </el-button>
      </div>
    </div>

    <el-table :data="requests" v-loading="loading" size="small" class="iam-table">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="user_name" :label="$t('message.iam.applicant')" width="110" />
      <el-table-column :label="$t('message.iam.type')" width="80">
        <template #default="{ row }">
          <el-tag :type="requestTypeTag(row.request_type)" size="small">{{ row.request_type_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.target')" min-width="140">
        <template #default="{ row }">
          {{ row.target_role_name || row.target_menu_name || row.target_menu_button_name || '-' }}
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
        layout="prev, pager, next, total" @update:currentPage="fetchPending" background size="small" />
    </div>

    <!-- Review Dialog -->
    <el-dialog v-model="reviewVisible"
      :title="reviewAction === 'approve' ? $t('message.iam.approveRequest') : $t('message.iam.rejectRequest')"
      width="440px" class="opsflow-dialog" destroy-on-close top="12vh">
      <div class="iam-review-info">
        <div class="iam-review-row"><span class="iam-review-label">{{ $t('message.iam.applicant') }}</span>{{ reviewRequest?.user_name }}</div>
        <div class="iam-review-row"><span class="iam-review-label">{{ $t('message.iam.type') }}</span>{{ reviewRequest?.request_type_label }}</div>
        <div class="iam-review-row"><span class="iam-review-label">{{ $t('message.iam.target') }}</span>{{ reviewRequest?.target_role_name || reviewRequest?.target_menu_name || '-' }}</div>
        <div class="iam-review-row"><span class="iam-review-label">{{ $t('message.iam.reason') }}</span>{{ reviewRequest?.reason }}</div>
      </div>
      <el-form label-width="80px" size="small">
        <el-form-item :label="$t('message.iam.reviewComment')">
          <el-input v-model="reviewComment" type="textarea" :rows="2"
            :placeholder="$t('message.iam.commentOptional')" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh, List } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { i18n } from '/@/i18n/index'
import { GetRequests, ApproveRequest, RejectRequest } from '/@/api/iam/requests'

const t = i18n.global.t

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

function onApprove(row: any) { reviewAction.value = 'approve'; reviewRequest.value = row; reviewComment.value = ''; reviewVisible.value = true }
function onReject(row: any) { reviewAction.value = 'reject'; reviewRequest.value = row; reviewComment.value = ''; reviewVisible.value = true }

async function confirmApprove() {
  if (!reviewRequest.value) return
  reviewLoading.value = true
  try {
    await ApproveRequest(reviewRequest.value.id, { review_comment: reviewComment.value })
    reviewVisible.value = false
    ElMessage.success(t('message.iam.approved'))
    await fetchPending()
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || t('message.iam.errors.approveFailed')) }
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
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || t('message.iam.errors.rejectFailed')) }
  reviewLoading.value = false
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
.iam-filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
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
.opsflow-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.opsflow-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }
</style>
