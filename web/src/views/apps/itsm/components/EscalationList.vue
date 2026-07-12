<template>
  <div>
    <div class="itsm-table-card">
      <div class="itsm-table-header">
        <span class="itsm-table-title">{{ $t('message.escalation.title') }}</span>
        <el-button size="small" type="primary" v-can="'itsm:escalation:manage'" @click="onCreate">
          <el-icon><Plus /></el-icon> {{ $t('message.common.create') }}
        </el-button>
      </div>
      <el-table :data="items" v-loading="loading" stripe style="width:100%" size="small"
        :empty-text="loading ? $t('message.itsmPage.loading') : $t('message.escalation.noData')">
        <el-table-column prop="level" :label="$t('message.escalation.level')" width="70" />
        <el-table-column prop="name" :label="$t('message.escalation.name')" min-width="160" />
        <el-table-column prop="timeout_minutes" :label="$t('message.escalation.timeoutLabel')" width="150" />
        <el-table-column prop="action" :label="$t('message.escalation.action')" width="140">
          <template #default="{ row }">{{ actionLabel(row.action) }}</template>
        </el-table-column>
        <el-table-column prop="is_active" :label="$t('message.itsmPage.colEnabled')" width="80" align="center">
          <template #default="{ row }"><el-switch v-model="row.is_active" size="small" @change="onToggle(row)" /></template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colActions')" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text v-can="'itsm:escalation:manage'" @click="onEdit(row)">{{ $t('message.common.edit') }}</el-button>
            <el-button size="small" text type="danger" v-can="'itsm:escalation:manage'" @click="onDelete(row)">{{ $t('message.common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="showEdit" :title="form.id ? $t('message.escalation.editEscalation') : $t('message.escalation.createEscalation')" width="480px" top="15vh" destroy-on-close append-to-body>
      <el-form :model="form" label-width="130px" size="small">
        <el-form-item :label="$t('message.escalation.levelNumber')"><el-input-number v-model="form.level" :min="1" :max="10" style="width:100%" /></el-form-item>
        <el-form-item :label="$t('message.escalation.name')"><el-input v-model="form.name" /></el-form-item>
        <el-form-item :label="$t('message.escalation.timeoutLabel')"><el-input-number v-model="form.timeout_minutes" :min="1" :max="43200" style="width:100%" /></el-form-item>
        <el-form-item :label="$t('message.escalation.action')">
          <el-select v-model="form.action" style="width:100%">
            <el-option :label="$t('message.escalation.notifyOnly')" value="notify_only" />
            <el-option :label="$t('message.escalation.transferLeader')" value="transfer_leader" />
            <el-option :label="$t('message.escalation.transferNext')" value="transfer_next" />
            <el-option :label="$t('message.escalation.notifyUsers')" value="notify_users" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.escalation.notifyUsersLabel')">
          <el-select v-model="notifyUsers" multiple filterable remote :remote-method="loadUsers"
            :loading="usersLoading" style="width:100%" :placeholder="$t('message.designer.searchUserPlaceholder')"
            @change="syncNotifyUsersStr">
            <el-option v-for="u in userOptions" :key="u.value" :label="u.label" :value="u.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.itsmPage.colEnabled')"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">{{ form.id ? $t('message.common.save') : $t('message.common.create') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { escalationApi } from '/@/api/itsm/index'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const { reportStats: updateHeroStats } = useHeroConsumer()

const loading = ref(false)
const items = ref<any[]>([])

const showEdit = ref(false)
const saving = ref(false)
const form = ref<any>({ level: 1, name: '', timeout_minutes: 60, action: 'notify_only', notify_users: '', is_active: true })
const notifyUsers = ref<string[]>([])
const userOptions = ref<any[]>([])
const usersLoading = ref(false)

function actionLabel(action: string): string {
  const m: Record<string, string> = { notify_only: '仅通知', transfer_leader: '转给组长', transfer_next: '升级到下一级', notify_users: '通知用户' }
  return m[action] || action
}

async function loadItems() {
  loading.value = true
  try { const res = await escalationApi.list(); items.value = res?.results || res?.data || res || []; reportStats() } finally { loading.value = false }
}

function reportStats() {
  updateHeroStats([
    { value: items.value.length, label: '层级总数' },
    { value: items.value.filter((e: any) => e.is_active).length, label: '已启用' },
  ])
}

function escExtractUsername(label: string): string {
  const m = label.match(/\((\w+)\)$/)
  return m ? m[1] : label
}

async function loadUsers() {
  usersLoading.value = true
  try {
    const { request } = await import('/@/utils/service')
    const res = await request({ url: '/api/iam/users/search/', method: 'get', params: { page_size: 10000 } })
    userOptions.value = ((res as any).data || []).map((item: any) => ({
      value: escExtractUsername(item.label),
      label: item.label,
    }))
  } catch { userOptions.value = [] }
  usersLoading.value = false
}

function syncNotifyUsersStr() {
  form.value.notify_users = notifyUsers.value.join(',')
}

function syncNotifyUsers() {
  const us = form.value.notify_users ? form.value.notify_users.split(',').filter(Boolean) : []
  notifyUsers.value = userOptions.value
    .filter(o => us.includes(o.value))
    .map(o => o.value)
}

function onCreate() {
  form.value = { level: 1, name: '', timeout_minutes: 60, action: 'notify_only', notify_users: '', is_active: true }
  notifyUsers.value = []
  showEdit.value = true
  loadUsers()
}

async function onEdit(row: any) {
  form.value = { ...row }
  showEdit.value = true
  await loadUsers()
  syncNotifyUsers()
}

async function onSave() {
  saving.value = true
  try {
    const data = { ...form.value }
    if (data.id) {
      await escalationApi.update(data.id, data)
    } else {
      await escalationApi.create(data)
    }
    ElMessage.success('保存成功')
    showEdit.value = false
    await loadItems()
  } catch { ElMessage.error('保存失败') }
  saving.value = false
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除升级级别「${row.name}」吗？`, '删除确认', { type: 'warning' })
    await escalationApi.delete(row.id)
    ElMessage.success('已删除')
    await loadItems()
  } catch { /* cancelled */ }
}

async function onToggle(row: any) {
  try { await escalationApi.update(row.id, { is_active: row.is_active }) } catch { row.is_active = !row.is_active }
}

onMounted(() => {
  if (props.active) loadItems()
})

watch(() => props.active, (isActive) => {
  if (isActive) {
    if (items.value.length === 0) loadItems()
    else reportStats()
  }
})
</script>
