<template>
  <div class="iam-section">
    <div class="iam-section-header">
      <span class="iam-section-title">
        <el-icon size="16"><OfficeBuilding /></el-icon>
        {{ $t('message.iam.business') }}
      </span>
      <el-button type="primary" size="small" :icon="Plus" @click="showForm(null)">
        {{ $t('message.iam.createBusiness') }}
      </el-button>
    </div>

    <el-table :data="businesses" v-loading="loading" size="small" class="iam-table">
      <el-table-column prop="name" :label="$t('message.iam.name')" min-width="160" />
      <el-table-column prop="code" :label="$t('message.iam.code')" width="120" />
      <el-table-column prop="group_name" :label="$t('message.iam.businessGroupLabel')" width="110" />
      <el-table-column :label="$t('message.iam.members')" width="80" align="center">
        <template #default="{ row }">{{ row.member_count ?? 0 }}</template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.status')" width="80" align="center">
        <template #default="{ row }">
          <span class="iam-status-dot" :class="row.is_active ? 'active' : 'inactive'" />
          {{ row.is_active ? 'Active' : 'Inactive' }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.iam.actions')" width="200" align="center">
        <template #default="{ row }">
          <el-button size="small" text @click="showForm(row)">{{ $t('message.iam.edit') }}</el-button>
          <el-button size="small" text @click="showMembers(row)">{{ $t('message.iam.members') }}</el-button>
          <el-button size="small" text type="danger" @click="confirmDelete(row)">{{ $t('message.iam.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && businesses.length === 0" :image-size="60" :description="$t('message.iam.noBusinesses')" />

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible"
      :title="editing ? $t('message.iam.editBusiness') : $t('message.iam.createBusiness')"
      width="460px" class="opsflow-dialog" destroy-on-close top="12vh">
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item :label="$t('message.iam.name')" required>
          <el-input v-model="form.name" maxlength="128" />
        </el-form-item>
        <el-form-item :label="$t('message.iam.code')" required>
          <el-input v-model="form.code" maxlength="32" />
        </el-form-item>
        <el-form-item :label="$t('message.iam.businessGroupLabel')">
          <el-select v-model="form.group" clearable style="width:100%" size="small">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.iam.businessActive')">
          <el-switch v-model="form.is_active" size="small" />
        </el-form-item>
        <el-form-item :label="$t('message.iam.dbAlias')">
          <el-input v-model="form.db_alias" maxlength="32" size="small"
            :placeholder="$t('message.iam.dbAliasHint')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="dialogVisible = false">{{ $t('message.iam.cancel') }}</el-button>
        <el-button size="small" type="primary" :loading="saving" @click="handleSave">{{ $t('message.iam.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- Members Dialog -->
    <el-dialog v-model="memberDialogVisible" :title="$t('message.iam.members')"
      width="460px" class="opsflow-dialog" destroy-on-close top="12vh">
      <div v-for="m in members" :key="m.id" class="iam-member-row">
        <span class="iam-member-name">{{ m.username }}{{ m.user_name ? ' (' + m.user_name + ')' : '' }}</span>
        <el-tag size="small" :type="m.role === 'admin' ? 'danger' : m.role === 'editor' ? 'warning' : 'info'">
          {{ m.role_label || m.role }}
        </el-tag>
        <el-button size="small" text type="danger" @click="handleRemoveMember(m.id)">
          {{ $t('message.iam.removeMember') }}
        </el-button>
      </div>
      <el-empty v-if="members.length === 0" :image-size="40" :description="$t('message.iam.noMembers')" />
      <div class="iam-add-row">
        <el-select v-model="newMember.user_id" :placeholder="$t('message.iam.selectUser')"
          style="width:180px" size="small" filterable />
        <el-select v-model="newMember.role" style="width:100px" size="small">
          <el-option :label="$t('message.iam.admin')" value="admin" />
          <el-option :label="$t('message.iam.editor')" value="editor" />
          <el-option :label="$t('message.iam.viewer')" value="viewer" />
        </el-select>
        <el-button size="small" type="primary" @click="handleAddMember">{{ $t('message.iam.addMember') }}</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, OfficeBuilding } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { i18n } from '/@/i18n/index'

const t = i18n.global.t
const loading = ref(false)
const saving = ref(false)
const businesses = ref<any[]>([])
const groups = ref<any[]>([])
const dialogVisible = ref(false)
const memberDialogVisible = ref(false)
const editing = ref<any>(null)
const currentBusiness = ref<any>(null)
const members = ref<any[]>([])
const newMember = ref({ user_id: null, role: 'editor' })
const form = ref({ name: '', code: '', group: null as number | null, is_active: true, db_alias: '' })

const fetchAll = async () => {
  loading.value = true
  try {
    const { default: request } = await import('/@/utils/request')
    const [bRes, gRes] = await Promise.all([
      request.get('/api/iam/businesses/'),
      request.get('/api/iam/business-groups/'),
    ])
    businesses.value = bRes.data || []
    groups.value = gRes.data || []
  } catch { /* ignore */ }
  loading.value = false
}

const fetchMembers = async (id: number) => {
  try {
    const { default: request } = await import('/@/utils/request')
    const res = await request.get(`/api/iam/businesses/${id}/members/`)
    members.value = res.data || []
  } catch { members.value = [] }
}

const showForm = (row: any) => {
  editing.value = row
  if (row) {
    form.value = { name: row.name, code: row.code, group: row.group || null, is_active: row.is_active, db_alias: row.db_alias || '' }
  } else {
    form.value = { name: '', code: '', group: null, is_active: true, db_alias: '' }
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  saving.value = true
  try {
    const { default: request } = await import('/@/utils/request')
    const payload = { ...form.value }
    if (editing.value) {
      await request.patch(`/api/iam/businesses/${editing.value.id}/`, payload)
      ElMessage.success(t('message.iam.updated'))
    } else {
      await request.post('/api/iam/businesses/', payload)
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
    await ElMessageBox.confirm(t('message.iam.deleteBusinessConfirm'), t('message.iam.delete'), { type: 'warning' })
    const { default: request } = await import('/@/utils/request')
    await request.delete(`/api/iam/businesses/${row.id}/`)
    ElMessage.success(t('message.iam.deleted'))
    fetchAll()
  } catch { /* cancelled */ }
}

const showMembers = async (row: any) => {
  currentBusiness.value = row
  await fetchMembers(row.id)
  memberDialogVisible.value = true
}

const handleAddMember = async () => {
  if (!newMember.value.user_id) return
  try {
    const { default: request } = await import('/@/utils/request')
    await request.post(`/api/iam/businesses/${currentBusiness.value.id}/members/`, newMember.value)
    ElMessage.success(t('message.iam.created'))
    newMember.value = { user_id: null, role: 'editor' }
    await fetchMembers(currentBusiness.value.id)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || t('message.iam.errors.saveFailed'))
  }
}

const handleRemoveMember = async (memberId: number) => {
  try {
    const { default: request } = await import('/@/utils/request')
    await request.delete(`/api/iam/businesses/${currentBusiness.value.id}/members/${memberId}/`)
    ElMessage.success(t('message.iam.deleted'))
    await fetchMembers(currentBusiness.value.id)
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
.iam-member-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid $g-border-card;
}
.iam-member-name { flex: 1; font-size: 13px; }
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
