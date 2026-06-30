<template>
  <div class="itsm-settings">
    <div class="itsm-settings-toolbar">
      <span class="itsm-settings-title">分派规则</span>
      <el-button type="primary" size="small" @click="openDialog()"><el-icon><Plus /></el-icon> 新建</el-button>
    </div>
    <div class="itsm-table-card">
      <el-table :data="list" v-loading="loading" stripe size="small" style="width:100%">
        <el-table-column prop="name" label="规则名" width="160" />
        <el-table-column prop="priority" label="优先级" width="70" />
        <el-table-column label="匹配分类" width="120">
          <template #default="{ row }">{{ row.match_category_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="匹配优先级" width="100">
          <template #default="{ row }">{{ row.match_priority || '-' }}</template>
        </el-table-column>
        <el-table-column label="匹配工单类型" width="120">
          <template #default="{ row }">{{ row.match_itsm_type || '-' }}</template>
        </el-table-column>
        <el-table-column label="目标技能组" width="120">
          <template #default="{ row }">{{ row.target_group_name || row.target_group }}</template>
        </el-table-column>
        <el-table-column label="分派模式" width="130">
          <template #default="{ row }">
            <el-tag size="small">{{ modeLabel(row.assign_mode) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="60">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" size="small" @click="toggleActive(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="openDialog(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingItem ? '编辑规则' : '新建规则'" width="520px" top="10vh" destroy-on-close>
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="1" :max="999" style="width:120px" />
        </el-form-item>
        <el-form-item label="匹配分类">
          <el-select v-model="form.match_category" clearable filterable style="width:100%" placeholder="留空=不限制">
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="匹配优先级">
          <el-select v-model="form.match_priority" clearable style="width:100%" placeholder="留空=不限制">
            <el-option label="P1" value="P1" /><el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" /><el-option label="P4" value="P4" />
          </el-select>
        </el-form-item>
        <el-form-item label="匹配工单类型">
          <el-select v-model="form.match_itsm_type" clearable style="width:100%" placeholder="留空=不限制">
            <el-option label="事件" value="incident" /><el-option label="变更" value="change" />
            <el-option label="服务请求" value="request" /><el-option label="问题" value="problem" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标技能组" :rules="[{ required: true, message: '必选' }]">
          <el-select v-model="form.target_group" filterable style="width:100%">
            <el-option v-for="g in groupOptions" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分派模式">
          <el-select v-model="form.assign_mode" style="width:100%">
            <el-option label="分派到组(待认领)" value="to_group" />
            <el-option label="分派到当前值班人" value="to_onduty" />
            <el-option label="分派到待办最少的人" value="least_busy" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
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
import { assignRuleApi, skillGroupApi } from '/@/api/itsm/index'
import { request } from '/@/utils/service'

const loading = ref(false)
const list = ref<any[]>([])
const dialogVisible = ref(false)
const saving = ref(false)
const editingItem = ref<any>(null)
const form = ref<any>({ name: '', priority: 100, match_category: null, match_priority: null, match_itsm_type: null, target_group: null, assign_mode: 'to_onduty', is_active: true })
const categoryOptions = ref<any[]>([])
const groupOptions = ref<any[]>([])

const MODE_LABELS: Record<string, string> = { to_group: '分派到组', to_onduty: '值班人', least_busy: '最少待办' }
function modeLabel(m: string) { return MODE_LABELS[m] || m }

async function loadList() {
  loading.value = true
  try { const res = await assignRuleApi.list(); list.value = res?.results || res?.data || [] } finally { loading.value = false }
}
async function loadOptions() {
  const [cRes, gRes] = await Promise.all([
    request({ url: '/api/itsm/service-categories/', method: 'get' }),
    skillGroupApi.list(),
  ])
  categoryOptions.value = (cRes as any).results || (cRes as any).data || []
  groupOptions.value = (gRes as any).results || (gRes as any).data || []
}
function openDialog(item?: any) {
  editingItem.value = item || null
  form.value = item ? { ...item } : { name: '', priority: 100, match_category: null, match_priority: null, match_itsm_type: null, target_group: null, assign_mode: 'to_onduty', is_active: true }
  if (!groupOptions.value.length) loadOptions()
  dialogVisible.value = true
}
async function onSave() {
  saving.value = true
  try {
    if (editingItem.value) await assignRuleApi.update(editingItem.value.id, form.value)
    else await assignRuleApi.create(form.value)
    ElMessage.success('保存成功'); dialogVisible.value = false
    await loadList()
  } catch { ElMessage.error('保存失败') }
  saving.value = false
}
async function onDelete(row: any) {
  await ElMessageBox.confirm('确定删除?')
  await assignRuleApi.delete(row.id); ElMessage.success('已删除'); await loadList()
}
async function toggleActive(row: any) {
  await assignRuleApi.update(row.id, { is_active: !row.is_active })
  await loadList()
}
onMounted(() => { loadList(); loadOptions() })
</script>

<style scoped>
.itsm-settings { padding: 4px 0; }
.itsm-settings-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.itsm-settings-title { font-size: 15px; font-weight: 600; color: #303133; }
</style>
