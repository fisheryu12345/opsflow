<template>
  <div class="my-requests">
    <div class="section-header">
      <span class="section-title">
        <el-icon size="16"><Tickets /></el-icon>
        My Requests
      </span>
      <el-button type="primary" :icon="Plus" @click="showCreateDialog">
        New Request
      </el-button>
    </div>

    <el-table :data="requests" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="Type" width="100">
        <template #default="{ row }">
          <el-tag :type="requestTypeTag(row.request_type)" size="small">{{ row.request_type_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Target" min-width="160">
        <template #default="{ row }">
          {{ row.target_role_name || row.target_menu_name || row.target_menu_button_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="Status" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small" effect="dark">{{ row.status_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reason" label="Reason" min-width="200" show-overflow-tooltip />
      <el-table-column label="Reviewer" width="120">
        <template #default="{ row }">{{ row.reviewer_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="Review Comment" width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.review_comment || '-' }}</template>
      </el-table-column>
      <el-table-column label="Created" width="160">
        <template #default="{ row }">{{ row.create_datetime }}</template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap" v-if="total > 0">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                     layout="prev, pager, next, total" @current-change="fetchRequests" />
    </div>

    <!-- Create Request Dialog -->
    <el-dialog v-model="createVisible" title="New Permission Request" width="520px" class="opsflow-dialog">
      <el-form label-width="100px">
        <el-form-item label="Request Type">
          <el-radio-group v-model="form.request_type">
            <el-radio label="role">Join Role</el-radio>
            <el-radio label="menu">Access Menu</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="Target" v-if="form.request_type === 'role'">
          <el-select v-model="form.target_role" placeholder="Select role" filterable style="width: 100%">
            <el-option v-for="r in availableRoles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Target" v-if="form.request_type === 'menu'">
          <el-select v-model="form.target_menu" placeholder="Select menu" filterable style="width: 100%">
            <el-option v-for="m in availableMenus" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Reason">
          <el-input v-model="form.reason" type="textarea" :rows="3" placeholder="Why do you need this permission?" />
          <div class="form-tip">Describe the reason for this permission request</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="submitting" @click="onCreate">Submit</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetRequests, CreateRequest } from '/@/api/iam/requests'
import { GetAvailableRoles, GetAvailableMenus } from '/@/api/iam/permissions'

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
    const [rolesRes, menusRes] = await Promise.all([GetAvailableRoles(), GetAvailableMenus()])
    availableRoles.value = rolesRes.data?.data || rolesRes.data || []
    availableMenus.value = menusRes.data?.data || menusRes.data || []
  } catch { /* ignore */ }
}

async function onCreate() {
  if (!form.value.reason) { ElMessage.warning('Please provide a reason'); return }
  if (form.value.request_type === 'role' && !form.value.target_role) { ElMessage.warning('Please select a role'); return }
  if (form.value.request_type === 'menu' && !form.value.target_menu) { ElMessage.warning('Please select a menu'); return }
  submitting.value = true
  try {
    await CreateRequest(form.value)
    createVisible.value = false
    ElMessage.success('Request submitted')
    await fetchRequests()
  } catch (e: any) { ElMessage.error(e?.msg || e?.message || 'Failed to submit') }
  submitting.value = false
}

onMounted(() => fetchRequests())
</script>

<style>
.my-requests {
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
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 12px 0 0;
  flex-shrink: 0;
}
.form-tip {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
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
