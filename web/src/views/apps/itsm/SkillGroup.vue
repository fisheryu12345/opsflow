<template>
  <div class="itsm-settings">
    <div class="itsm-settings-toolbar">
      <span class="itsm-settings-title">{{ $t('message.skillGroup.title') }}</span>
      <el-button type="primary" size="small" @click="openDialog()">
        <el-icon><Plus /></el-icon> {{ $t('message.common.create') }}
      </el-button>
    </div>
    <div class="itsm-table-card">
      <el-table :data="list" v-loading="loading" stripe size="small" style="width:100%">
        <el-table-column prop="name" :label="$t('message.skillGroup.name')" width="140" />
        <el-table-column prop="code" :label="$t('message.skillGroup.code')" width="100" />
        <el-table-column :label="$t('message.skillGroup.leader')" width="120">
          <template #default="{ row }">{{ row.leader_name || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('message.skillGroup.members')" width="80">
          <template #default="{ row }">{{ (row.members || []).length }}</template>
        </el-table-column>
        <el-table-column prop="description" :label="$t('message.skillGroup.description')" min-width="160" show-overflow-tooltip />
        <el-table-column :label="$t('message.skillGroup.status')" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? $t('message.common.enabled') : $t('message.common.disabled') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colActions')" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="openDialog(row)">{{ $t('message.common.edit') }}</el-button>
            <el-button size="small" text @click="manageMembers(row)">{{ $t('message.skillGroup.memberManage') }}</el-button>
            <el-button size="small" text type="danger" @click="onDelete(row)">{{ $t('message.common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingItem ? $t('message.common.edit') : $t('message.common.create')" width="520px" top="10vh" destroy-on-close append-to-body>
      <el-form ref="formRef" :model="form" label-width="80px" size="small">
        <el-form-item :label="$t('message.skillGroup.name')" prop="name" :rules="[{ required: true, message: t('message.skillGroup.name') }]">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item :label="$t('message.skillGroup.code')" prop="code" :rules="[{ required: true, message: t('message.skillGroup.code') }]">
          <el-input v-model="form.code" />
        </el-form-item>
        <el-form-item :label="$t('message.skillGroup.leader')">
          <el-select v-model="form.leader" filterable clearable style="width:100%" :placeholder="$t('message.skillGroup.selectUser')">
            <el-option v-for="u in userOptions" :key="u.id" :label="`${u.name} (${u.username})`" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.skillGroup.description')">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="$t('message.itsmPage.colEnabled')">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">{{ $t('message.common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="membersVisible" :title="$t('message.skillGroup.memberTitle', { name: editingGroupName })" width="480px" top="10vh" destroy-on-close append-to-body>
      <div class="sg-member-list">
        <div v-for="m in form.members" :key="m.id" class="sg-member-row">
          <span>{{ m.name }} ({{ m.username }})</span>
          <el-button size="small" text type="danger" @click="removeMember(m.id)">{{ $t('message.skillGroup.removeMember') }}</el-button>
        </div>
        <div v-if="!form.members.length" style="color:#C0C4CC;font-size:12px;padding:8px 0">{{ $t('message.skillGroup.noMembers') }}</div>
      </div>
      <div class="sg-add-row">
        <el-select v-model="addUserId" filterable style="width:240px" size="small" :placeholder="$t('message.skillGroup.selectUser')">
          <el-option v-for="u in userOptions" :key="u.id" :label="`${u.name} (${u.username})`" :value="u.id" />
        </el-select>
        <el-button size="small" type="primary" :disabled="!addUserId" @click="addMember">{{ $t('message.skillGroup.addMember') }}</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { skillGroupApi, AddSkillGroupMember, RemoveSkillGroupMember } from '/@/api/itsm/index'
import { request } from '/@/utils/service'

const { t } = useI18n()

const loading = ref(false)
const list = ref<any[]>([])
const dialogVisible = ref(false)
const saving = ref(false)
const editingItem = ref<any>(null)
const form = ref<any>({ name: '', code: '', leader: null, description: '', is_active: true, members: [] })
const userOptions = ref<any[]>([])
const membersVisible = ref(false)
const addUserId = ref<number | null>(null)
const editingGroupName = ref('')

async function loadList() {
  loading.value = true
  try { const res = await skillGroupApi.list(); list.value = res?.results || res?.data || [] } finally { loading.value = false }
}
async function loadUsers() {
  try {
    const res: any = await request({ url: '/api/iam/users/search/', method: 'get', params: { page_size: 5000 } })
    userOptions.value = (res.data || []).map((item: any) => ({ id: item.value, name: item.label }))
  } catch { userOptions.value = [] }
}
function openDialog(item?: any) {
  editingItem.value = item || null
  if (item) { form.value = { ...item, leader: item.leader || null, members: item.members || [] } }
  else { form.value = { name: '', code: '', leader: null, description: '', is_active: true, members: [] } }
  if (!userOptions.value.length) loadUsers()
  dialogVisible.value = true
}
async function onSave() {
  saving.value = true
  try {
    if (editingItem.value) { await skillGroupApi.update(editingItem.value.id, form.value) }
    else { await skillGroupApi.create(form.value) }
    ElMessage.success(t('message.common.saveSuccess'))
    dialogVisible.value = false
    await loadList()
  } catch { ElMessage.error(t('message.common.saveFailed')) }
  saving.value = false
}
async function onDelete(row: any) {
  await ElMessageBox.confirm(t('message.common.deleteConfirm'))
  await skillGroupApi.delete(row.id)
  ElMessage.success(t('message.common.deleted'))
  await loadList()
}
async function manageMembers(row: any) {
  editingItem.value = row
  editingGroupName.value = row.name
  form.value.members = (row.members || []).map((m: any) => typeof m === 'object' ? m : { id: m })
  membersVisible.value = true
  addUserId.value = null
}
async function addMember() {
  if (!addUserId.value || !editingItem.value) return
  await AddSkillGroupMember(editingItem.value.id, addUserId.value)
  addUserId.value = null
  await loadList()
  form.value.members = (list.value.find((x: any) => x.id === editingItem.value.id)?.members || [])
    .map((m: any) => typeof m === 'object' ? m : { id: m })
}
async function removeMember(userId: number) {
  if (!editingItem.value) return
  await RemoveSkillGroupMember(editingItem.value.id, userId)
  await loadList()
  form.value.members = form.value.members.filter((m: any) => m.id !== userId)
}
onMounted(loadList)
</script>

<style scoped>
.itsm-settings { padding: 4px 0; }
.itsm-settings-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.itsm-settings-title { font-size: 15px; font-weight: 600; color: #303133; }
.sg-member-list { max-height: 300px; overflow-y: auto; }
.sg-member-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; border-bottom: 1px solid #eee; font-size: 13px; }
.sg-add-row { display: flex; gap: 8px; align-items: center; margin-top: 12px; padding-top: 12px; border-top: 1px solid #e4e7ed; }
</style>
