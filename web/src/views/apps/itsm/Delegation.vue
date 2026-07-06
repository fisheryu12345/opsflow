<template>
  <div class="itsm-delegation">
    <!-- Toolbar -->
    <div class="itsm-delegation-toolbar">
      <span class="itsm-delegation-title">我的审批委托</span>
      <el-button type="primary" size="small" v-can="'itsm:ticket:assign'" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建委托
      </el-button>
    </div>

    <!-- Delegation List -->
    <div class="itsm-table-card">
      <el-table :data="list" v-loading="loading" stripe style="width:100%" size="small"
        :empty-text="'暂无委托规则'">
        <el-table-column label="委托人" width="120">
          <template #default="{ row }">
            {{ row.user_name || row.user }}
          </template>
        </el-table-column>
        <el-table-column label="被委托人" width="120">
          <template #default="{ row }">
            {{ row.delegate_to_name || row.delegate_to }}
          </template>
        </el-table-column>
        <el-table-column label="工单类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.ticket_type" size="small">{{ row.ticket_type }}</el-tag>
            <span v-else class="itsm-delegation-all">全部类型</span>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.date_from) }}
          </template>
        </el-table-column>
        <el-table-column label="结束时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.date_to) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" size="small"
              @click="onToggleActive(row)" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="itsm-delegation-remark">{{ row.remark || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text v-can="'itsm:ticket:assign'" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" text type="danger" v-can="'itsm:ticket:assign'" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑委托' : '新建委托'" width="520px" top="8vh" class="itsm-dialog" append-to-body>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="被委托人" prop="delegate_to">
          <el-select v-model="form.delegate_to" filterable remote :remote-method="searchUsers"
            :loading="searching" placeholder="搜索用户" style="width:100%"
            value-key="id">
            <el-option v-for="u in userOptions" :key="u.id" :label="u.name + ' (' + u.username + ')'" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="工单类型" prop="ticket_type">
          <el-select v-model="form.ticket_type" clearable placeholder="全部类型" style="width:100%">
            <el-option label="变更申请" value="change" />
            <el-option label="事件工单" value="incident" />
            <el-option label="服务请求" value="request" />
            <el-option label="问题管理" value="problem" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间" prop="date_from">
          <el-date-picker v-model="form.date_from" type="datetime" placeholder="选择开始时间"
            style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="结束时间" prop="date_to">
          <el-date-picker v-model="form.date_to" type="datetime" placeholder="选择结束时间"
            style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="委托原因（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :icon="Check" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Check } from '@element-plus/icons-vue'
import { delegationApi, ToggleDelegation } from '/@/api/itsm/index'
import { GetList } from '/@/views/apps/iam/admin/user/api'

const { t } = useI18n()

// ===== Data =====
const loading = ref(false)
const list = ref<any[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const formRef = ref<any>(null)

const form = ref<any>({
  delegate_to: null,
  ticket_type: '',
  date_from: '',
  date_to: '',
  remark: '',
})

const rules = {
  delegate_to: [{ required: true, message: '请选择被委托人', trigger: 'change' }],
  date_from: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  date_to: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
}

// ===== User search =====
const searching = ref(false)
const userOptions = ref<any[]>([])

async function searchUsers(query: string) {
  if (!query) return
  searching.value = true
  try {
    const res = await GetList({ page: 1, limit: 20, search: query })
    userOptions.value = res?.results || res?.data || []
  } finally {
    searching.value = false
  }
}

// ===== Load =====
async function loadList() {
  loading.value = true
  try {
    const res = await delegationApi.list()
    list.value = res?.results || res?.data || []
  } finally {
    loading.value = false
  }
}

// ===== CRUD =====
function openCreate() {
  isEdit.value = false
  form.value = { delegate_to: null, ticket_type: '', date_from: '', date_to: '', remark: '' }
  userOptions.value = []
  dialogVisible.value = true
}

function openEdit(row: any) {
  isEdit.value = true
  form.value = {
    id: row.id,
    delegate_to: row.delegate_to,
    ticket_type: row.ticket_type || '',
    date_from: row.date_from,
    date_to: row.date_to,
    remark: row.remark || '',
  }
  // Load the user display
  if (row.delegate_to) {
    searchUsers('')
  }
  dialogVisible.value = true
}

async function onSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value) {
      await delegationApi.update(form.value.id, form.value)
      ElMessage.success('委托已更新')
    } else {
      await delegationApi.create(form.value)
      ElMessage.success('委托已创建')
    }
    dialogVisible.value = false
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.msg || '保存失败')
  } finally {
    saving.value = false
  }
}

async function onDelete(row: any) {
  await ElMessageBox.confirm('确定删除该委托规则？', '删除确认')
  try {
    await delegationApi.delete(row.id)
    ElMessage.success('已删除')
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.msg || '删除失败')
  }
}

async function onToggleActive(row: any) {
  try {
    await ToggleDelegation(row.id)
    row.is_active = !row.is_active
    ElMessage.success(row.is_active ? '已启用' : '已停用')
  } catch (e: any) {
    ElMessage.error(e?.msg || '操作失败')
  }
}

function formatDate(d: string) {
  if (!d) return '-'
  return d.slice(0, 16).replace('T', ' ')
}

onMounted(loadList)
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.itsm-delegation {
  padding-top: 16px;
}

.itsm-delegation-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.itsm-delegation-title {
  font-size: 15px;
  font-weight: 600;
  color: $g-text-primary;
}

.itsm-delegation-all {
  color: $g-text-muted;
  font-size: 12px;
}

.itsm-delegation-remark {
  color: $g-text-secondary;
  font-size: 12px;
}

.itsm-table-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: $g-shadow-card;
  overflow: hidden;
}

.itsm-table-card :deep(.el-table th.el-table__cell) {
  background: #fafafa;
  color: #606266;
  font-weight: 600;
  font-size: 12px;
}

.itsm-table-card :deep(.el-table__body tr:hover td) {
  background: #f5f7fa;
}
</style>
