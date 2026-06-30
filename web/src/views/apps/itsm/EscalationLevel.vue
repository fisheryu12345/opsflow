<template>
  <div class="itsm-settings">
    <div class="itsm-settings-toolbar">
      <span class="itsm-settings-title">升级级别</span>
      <el-button type="primary" size="small" @click="openDialog()"><el-icon><Plus /></el-icon> 新建</el-button>
    </div>
    <div class="itsm-table-card">
      <el-table :data="list" v-loading="loading" stripe size="small" style="width:100%">
        <el-table-column prop="name" label="级别名" width="120" />
        <el-table-column prop="level" label="级别" width="60" />
        <el-table-column label="技能组" width="140">
          <template #default="{ row }">{{ row.group_name || row.group }}</template>
        </el-table-column>
        <el-table-column prop="timeout_minutes" label="超时(分钟)" width="110" />
        <el-table-column label="动作" width="150">
          <template #default="{ row }">{{ actionLabel(row.action) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="openDialog(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingItem ? '编辑升级级别' : '新建升级级别'" width="520px" top="10vh" destroy-on-close>
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="级别名称" prop="name">
          <el-input v-model="form.name" placeholder="如 L1" />
        </el-form-item>
        <el-form-item label="升级顺序">
          <el-input-number v-model="form.level" :min="1" :max="10" style="width:120px" />
        </el-form-item>
        <el-form-item label="所属技能组" :rules="[{ required: true, message: '必选' }]">
          <el-select v-model="form.group" filterable style="width:100%">
            <el-option v-for="g in groupOptions" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="超时阈值" :rules="[{ required: true, message: '必填' }]">
          <el-input-number v-model="form.timeout_minutes" :min="1" :max="10080" style="width:140px" />
          <span style="font-size:12px;color:#909399;margin-left:8px">分钟</span>
        </el-form-item>
        <el-form-item label="超时动作">
          <el-select v-model="form.action" style="width:100%">
            <el-option label="仅通知" value="notify_only" />
            <el-option label="转给组长" value="transfer_to_leader" />
            <el-option label="升级到下一级" value="transfer_to_next_level" />
          </el-select>
        </el-form-item>
        <el-form-item label="通知用户">
          <el-select v-model="form.notify_users" multiple filterable collapse-tags style="width:100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="`${u.name} (${u.username})`" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { escalationLevelApi, skillGroupApi } from '/@/api/itsm/index'
import { request } from '/@/utils/service'

const loading = ref(false)
const list = ref<any[]>([])
const dialogVisible = ref(false)
const saving = ref(false)
const editingItem = ref<any>(null)
const form = ref<any>({ name: '', level: 1, group: null, timeout_minutes: 60, action: 'transfer_to_next_level', notify_users: [] })
const groupOptions = ref<any[]>([])
const userOptions = ref<any[]>([])

const ACTION_LABELS: Record<string, string> = { notify_only: '仅通知', transfer_to_leader: '转给组长', transfer_to_next_level: '升级到下一级' }
function actionLabel(a: string) { return ACTION_LABELS[a] || a }

async function loadList() {
  loading.value = true
  try { const res = await escalationLevelApi.list(); list.value = res?.results || res?.data || [] } finally { loading.value = false }
}
async function loadOptions() {
  const [gRes, uRes] = await Promise.all([
    skillGroupApi.list(),
    request({ url: '/api/system/user/', method: 'get', params: { page_size: 5000 } }),
  ])
  groupOptions.value = (gRes as any).results || (gRes as any).data || []
  userOptions.value = (uRes as any).data?.results || (uRes as any).data || []
}
function openDialog(item?: any) {
  editingItem.value = item || null
  form.value = item ? { ...item, notify_users: item.notify_users || [] } : { name: '', level: 1, group: null, timeout_minutes: 60, action: 'transfer_to_next_level', notify_users: [] }
  if (!groupOptions.value.length) loadOptions()
  dialogVisible.value = true
}
async function onSave() {
  saving.value = true
  try {
    if (editingItem.value) await escalationLevelApi.update(editingItem.value.id, form.value)
    else await escalationLevelApi.create(form.value)
    ElMessage.success('保存成功'); dialogVisible.value = false; await loadList()
  } catch { ElMessage.error('保存失败') }
  saving.value = false
}
async function onDelete(row: any) {
  await ElMessageBox.confirm('确定删除?')
  await escalationLevelApi.delete(row.id); ElMessage.success('已删除'); await loadList()
}
onMounted(() => { loadList(); loadOptions() })
</script>

<style scoped>
.itsm-settings { padding: 4px 0; }
.itsm-settings-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.itsm-settings-title { font-size: 15px; font-weight: 600; color: #303133; }
</style>
