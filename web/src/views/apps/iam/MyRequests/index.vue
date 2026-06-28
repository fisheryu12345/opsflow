<template>
  <div class="iam-section">
    <div class="iam-section-header">
      <span class="iam-section-title">
        <el-icon size="16"><Tickets /></el-icon>
        {{ $t('message.iam.myRequests') }}
      </span>
      <el-button type="primary" size="small" :icon="Plus" @click="showCreateDialog">
        {{ $t('message.iam.newRequest') }}
      </el-button>
    </div>

    <el-table :data="requests" v-loading="loading" size="small" class="iam-table">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column :label="$t('message.iam.type')" width="90">
        <template #default="{ row }">
          <el-tag :type="requestTypeTag(row.request_type)" size="small">{{ row.request_type_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.target')" min-width="140">
        <template #default="{ row }">
          {{ row.target_role_name || row.target_menu_name || row.target_menu_button_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.status')" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small" effect="dark">{{ row.status_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reason" :label="$t('message.iam.reason')" min-width="160" show-overflow-tooltip />
      <el-table-column :label="$t('message.iam.reviewer')" width="100">
        <template #default="{ row }">{{ row.reviewer_name || '-' }}</template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.reviewComment')" width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.review_comment || '-' }}</template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.createdAt')" width="150">
        <template #default="{ row }">{{ row.create_datetime }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && requests.length === 0" :image-size="60" :description="$t('message.iam.noRequests')" />

    <div class="iam-pagination" v-if="total > 0">
      <el-pagination v-model:currentPage="page" :page-size="pageSize" :total="total"
        layout="prev, pager, next, total" @update:currentPage="fetchRequests" background size="small" />
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="createVisible" :title="$t('message.iam.newRequest')" width="480px"
      class="opsflow-dialog" destroy-on-close top="12vh">
      <el-form label-width="90px" size="small">
        <el-form-item :label="$t('message.iam.requestType')">
          <el-radio-group v-model="form.request_type">
            <el-radio label="role">{{ $t('message.iam.joinRole') }}</el-radio>
            <el-radio label="menu">{{ $t('message.iam.accessMenu') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('message.iam.target')" v-if="form.request_type === 'role'">
          <el-select v-model="form.target_role" :placeholder="$t('message.iam.selectRole')"
            filterable style="width:100%" size="small">
            <el-option v-for="r in availableRoles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.iam.target')" v-if="form.request_type === 'menu'">
          <el-select v-model="form.target_menu" :placeholder="$t('message.iam.selectMenu')"
            filterable style="width:100%" size="small">
            <el-option v-for="m in availableMenus" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.iam.reason')">
          <el-input v-model="form.reason" type="textarea" :rows="3"
            :placeholder="$t('message.iam.reasonPlaceholder')" />
          <span class="iam-form-tip">{{ $t('message.iam.reasonTip') }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="createVisible = false">{{ $t('message.iam.cancel') }}</el-button>
        <el-button size="small" type="primary" :loading="submitting" @click="onCreate">
          {{ $t('message.iam.submit') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { i18n } from '/@/i18n/index'
import { GetRequests, CreateRequest } from '/@/api/iam/requests'
import { GetAvailableRoles, GetAvailableMenus } from '/@/api/iam/permissions'

const t = i18n.global.t

const requests = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const createVisible = ref(false)
const submitting = ref(false)
const availableRoles = ref<any[]>([])
const availableMenus = ref<any[]>([])
const form = ref<any>({ request_type: 'role', target_role: null, target_menu: null, reason: '' })

function requestTypeTag(type: string) {
  const map: Record<string, string> = { role: 'success', menu: 'primary', menu_button: 'warning' }
  return map[type] || 'info'
}
function statusTag(status: string) {
  const map: Record<string, string> = { pending: 'warning', approved: 'success', rejected: 'danger' }
  return map[status] || 'info'
}

async function fetchRequests() {
  loading.value = true
  try {
    const res = await GetRequests({ page: page.value, limit: pageSize.value })
    requests.value = res.data || []
    total.value = res.total || 0
  } catch { /* ignore */ }
  loading.value = false
}

async function showCreateDialog() {
  form.value = { request_type: 'role', target_role: null, target_menu: null, reason: '' }
  createVisible.value = true
  try {
    const [r, m] = await Promise.all([GetAvailableRoles(), GetAvailableMenus()])
    availableRoles.value = r.data?.data || r.data || []
    availableMenus.value = m.data?.data || m.data || []
  } catch { /* ignore */ }
}

async function onCreate() {
  if (!form.value.reason) { ElMessage.warning(t('message.iam.errors.reasonRequired')); return }
  if (form.value.request_type === 'role' && !form.value.target_role) { ElMessage.warning(t('message.iam.errors.roleRequired')); return }
  if (form.value.request_type === 'menu' && !form.value.target_menu) { ElMessage.warning(t('message.iam.errors.menuRequired')); return }
  submitting.value = true
  try {
    await CreateRequest(form.value)
    createVisible.value = false
    ElMessage.success(t('message.iam.submitted'))
    await fetchRequests()
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || t('message.iam.errors.submitFailed')) }
  submitting.value = false
}

onMounted(() => fetchRequests())
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
.iam-table {
  width: 100%;
}
.iam-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}
.iam-form-tip {
  font-size: 11px;
  color: $g-text-muted;
  margin-top: 2px;
}
.opsflow-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.opsflow-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }
</style>
