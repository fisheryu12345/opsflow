<template>
  <div class="rule-page">
    <div class="rule-header">
      <h2 class="rule-title">告警分派规则</h2>
      <el-button type="primary" size="small" @click="showDialog=true">新建规则组</el-button>
    </div>
    <div class="rule-body">
      <el-table :data="groups" stripe size="small" v-loading="loading" style="width:100%">
        <el-table-column label="优先级" width="80">
          <template #default="{row}">{{ row.priority >= 0 ? 'P' + row.priority : '-' }}</template>
        </el-table-column>
        <el-table-column prop="name" label="规则组名" min-width="160" />
        <el-table-column label="规则数" width="80">
          <template #default="{row}">{{ row.rules?.length || 0 }}</template>
        </el-table-column>
        <el-table-column label="启用" width="80">
          <template #default="{row}"><el-switch :model-value="row.is_enabled" size="small" /></template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{row}">
            <el-button size="small" text @click="editGroup(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="deleteGroup(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showDialog" :title="editing ? '编辑规则组' : '新建规则组'" width="600px">
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="0" :max="99" />
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" :icon="Check" @click="saveGroup">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { assignGroupApi } from '/@/api/monitor/index'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const groups = ref<any[]>([])
const showDialog = ref(false)
const editing = ref(false)
const form = reactive({ name: '', priority: 0, is_enabled: true })

async function loadGroups() {
  loading.value = true
  try { const r = await assignGroupApi.list(); groups.value = r.data || [] }
  finally { loading.value = false }
}
function editGroup(row: any) { Object.assign(form, { name: row.name, priority: row.priority, is_enabled: row.is_enabled }); editing.value = true; showDialog.value = true }
function deleteGroup(row: any) { assignGroupApi.delete(row.id).then(() => { ElMessage.success('已删除'); loadGroups() }) }
async function saveGroup() {
  if (editing.value) await assignGroupApi.update(groups.value.find((g:any) => g.name === form.name)?.id, form)
  else await assignGroupApi.create(form)
  ElMessage.success('保存成功'); showDialog.value = false; loadGroups()
}
onMounted(() => loadGroups())
</script>

<style scoped>
.rule-page { padding:20px; }
.rule-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.rule-title { margin:0; font-size:18px; font-weight:600; }
.rule-body { background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 4px rgba(0,0,0,0.06); }
</style>
