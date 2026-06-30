<template>
  <div class="iam-section">
    <div class="iam-section-header">
      <span class="iam-section-title">
        <el-icon size="16"><Monitor /></el-icon>
        {{ $t('message.iam.environment') }}
      </span>
      <el-button type="primary" size="small" :icon="Plus" @click="showForm(null)">
        {{ $t('message.iam.createEnv') }}
      </el-button>
    </div>

    <el-table :data="environments" v-loading="loading" size="small" class="iam-table">
      <el-table-column prop="name" :label="$t('message.iam.name')" min-width="150" />
      <el-table-column prop="code" :label="$t('message.iam.code')" width="100" />
      <el-table-column :label="$t('message.iam.riskLevel')" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="riskTag(row.risk_level)" size="small">{{ row.risk_level }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.status')" width="80" align="center">
        <template #default="{ row }">
          <span class="iam-status-dot" :class="row.is_active ? 'active' : 'inactive'" />
          {{ row.is_active ? 'Active' : 'Inactive' }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.actions')" width="260" align="center">
        <template #default="{ row }">
          <el-button size="small" text @click="showForm(row)">{{ $t('message.iam.edit') }}</el-button>
          <el-button size="small" text @click="showPermissions(row)">{{ $t('message.iam.permissions') }}</el-button>
          <el-button size="small" text type="danger" @click="confirmDelete(row)">{{ $t('message.iam.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && environments.length === 0" :image-size="60" :description="$t('message.iam.noEnvironments')" />

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible"
      :title="editing ? $t('message.iam.editEnv') : $t('message.iam.createEnv')"
      width="400px" class="opsflow-dialog" destroy-on-close top="12vh" append-to-body>
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item :label="$t('message.iam.name')" required>
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item :label="$t('message.iam.code')" required>
          <el-input v-model="form.code" maxlength="16" />
        </el-form-item>
        <el-form-item :label="$t('message.iam.riskLevel')">
          <el-input-number v-model="form.risk_level" :min="0" :max="100" :step="10" size="small" />
        </el-form-item>
        <el-form-item :label="$t('message.iam.status')">
          <el-switch v-model="form.is_active" size="small" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="dialogVisible = false">{{ $t('message.iam.cancel') }}</el-button>
        <el-button size="small" type="primary" :loading="saving" @click="handleSave">{{ $t('message.iam.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- Permissions Dialog -->
    <el-dialog v-model="permDialogVisible" :title="$t('message.iam.permissions')"
      width="480px" class="opsflow-dialog" destroy-on-close top="12vh" append-to-body>
      <div v-for="p in permissions" :key="p.id" class="iam-perm-row">
        <span class="iam-perm-name">{{ p.username }}{{ p.user_name ? ' (' + p.user_name + ')' : '' }}</span>
        <el-tag size="small" :type="p.can_execute ? 'success' : 'info'">
          {{ p.can_execute ? $t('message.iam.canExecute') : $t('message.iam.noPermission') }}
        </el-tag>
        <el-button size="small" text type="danger" @click="handleRevokePermission(p.id)">
          {{ $t('message.iam.revokePermission') }}
        </el-button>
      </div>
      <el-empty v-if="permissions.length === 0" :image-size="40" :description="$t('message.iam.noPermissions')" />
      <div class="iam-add-row">
        <el-select v-model="newPerm.user_id" :placeholder="$t('message.iam.selectUser')"
          style="width:180px" size="small" filterable />
        <el-checkbox v-model="newPerm.can_execute" size="small">{{ $t('message.iam.canExecute') }}</el-checkbox>
        <el-button size="small" type="primary" @click="handleGrantPermission">{{ $t('message.iam.grantPermission') }}</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Monitor } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { i18n } from '/@/i18n/index'

const t = i18n.global.t
const loading = ref(false)
const saving = ref(false)
const environments = ref<any[]>([])
const dialogVisible = ref(false)
const permDialogVisible = ref(false)
const editing = ref<any>(null)
const currentEnv = ref<any>(null)
const permissions = ref<any[]>([])
const newPerm = ref({ user_id: null, can_execute: true })
const form = ref({ name: '', code: '', risk_level: 0, is_active: true })

const riskTag = (level: number) => level >= 100 ? 'danger' : level >= 50 ? 'warning' : 'success'

const fetchAll = async () => {
  loading.value = true
  try {
    const { default: request } = await import('/@/utils/request')
    const res = await request.get('/api/iam/environments/')
    environments.value = res.data || []
  } finally { loading.value = false }
}

const fetchPermissions = async (id: number) => {
  try {
    const { default: request } = await import('/@/utils/request')
    const res = await request.get(`/api/iam/environments/${id}/permissions/`)
    permissions.value = res.data || []
  } catch { permissions.value = [] }
}

const showForm = (row: any) => {
  editing.value = row
  form.value = row
    ? { name: row.name, code: row.code, risk_level: row.risk_level, is_active: row.is_active }
    : { name: '', code: '', risk_level: 0, is_active: true }
  dialogVisible.value = true
}

const handleSave = async () => {
  saving.value = true
  try {
    const { default: request } = await import('/@/utils/request')
    if (editing.value) {
      await request.patch(`/api/iam/environments/${editing.value.id}/`, form.value)
      ElMessage.success(t('message.iam.updated'))
    } else {
      await request.post('/api/iam/environments/', form.value)
      ElMessage.success(t('message.iam.created'))
    }
    dialogVisible.value = false
    fetchAll()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || t('message.iam.errors.saveFailed'))
  }
  saving.value = false
}

const confirmDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(t('message.iam.deleteEnvConfirm', { name: row.name }), t('message.iam.delete'), { type: 'warning' })
    const { default: request } = await import('/@/utils/request')
    await request.delete(`/api/iam/environments/${row.id}/`)
    ElMessage.success(t('message.iam.deleted'))
    fetchAll()
  } catch { /* cancelled */ }
}

const showPermissions = async (row: any) => {
  currentEnv.value = row
  await fetchPermissions(row.id)
  permDialogVisible.value = true
}

const handleGrantPermission = async () => {
  if (!newPerm.value.user_id) return
  try {
    const { default: request } = await import('/@/utils/request')
    await request.post(`/api/iam/environments/${currentEnv.value.id}/permissions/`, newPerm.value)
    ElMessage.success(t('message.iam.created'))
    newPerm.value = { user_id: null, can_execute: true }
    await fetchPermissions(currentEnv.value.id)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || t('message.iam.errors.saveFailed'))
  }
}

const handleRevokePermission = async (permId: number) => {
  try {
    const { default: request } = await import('/@/utils/request')
    await request.delete(`/api/iam/environments/${currentEnv.value.id}/permissions/${permId}/`)
    ElMessage.success(t('message.iam.deleted'))
    await fetchPermissions(currentEnv.value.id)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || t('message.iam.errors.deleteFailed'))
  }
}

onMounted(() => fetchAll())
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
.iam-table { width: 100%; }
.iam-status-dot {
  display: inline-block;
  width: 6px; height: 6px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
  &.active { background: $g-color-success; }
  &.inactive { background: $g-text-muted; }
}
.iam-perm-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid $g-border-card;
}
.iam-perm-name { flex: 1; font-size: 13px; }
.iam-add-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid $g-border-default;
}
.opsflow-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.opsflow-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }
</style>
