<template>
  <div class="itsm-settings">
    <div class="itsm-settings-toolbar">
      <span class="itsm-settings-title">{{ $t('message.onDuty.title') }}</span>
      <div style="display:flex;gap:8px">
        <el-date-picker v-model="filterDate" type="date" size="small" :placeholder="$t('message.onDuty.filterDate')" value-format="YYYY-MM-DD"
          @change="loadList" />
        <el-button type="primary" size="small" @click="openDialog()"><el-icon><Plus /></el-icon> {{ $t('message.common.create') }}</el-button>
      </div>
    </div>
    <div class="itsm-table-card">
      <el-table :data="list" v-loading="loading" stripe size="small" style="width:100%">
        <el-table-column prop="duty_date" :label="$t('message.onDuty.date')" width="120" />
        <el-table-column :label="$t('message.onDuty.group')" width="140">
          <template #default="{ row }">{{ row.group_name || row.group }}</template>
        </el-table-column>
        <el-table-column :label="$t('message.onDuty.user')" width="120">
          <template #default="{ row }">{{ row.user_name || row.user }}</template>
        </el-table-column>
        <el-table-column :label="$t('message.onDuty.dutyType')" width="80">
          <template #default="{ row }">
            <el-tag :type="row.duty_type === 'primary' ? 'primary' : 'warning'" size="small">
              {{ row.duty_type === 'primary' ? '主班' : '备班' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colActions')" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="openDialog(row)">{{ $t('message.common.edit') }}</el-button>
            <el-button size="small" text type="danger" @click="onDelete(row)">{{ $t('message.common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingItem ? t('message.onDuty.title') : t('message.common.create')" width="420px" top="15vh" destroy-on-close>
      <el-form :model="form" label-width="80px" size="small">
        <el-form-item :label="$t('message.onDuty.group')" :rules="[{ required: true, message: '必选' }]">
          <el-select v-model="form.group" filterable style="width:100%">
            <el-option v-for="g in groupOptions" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.onDuty.user')" :rules="[{ required: true, message: '必选' }]">
          <el-select v-model="form.user" filterable style="width:100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="`${u.name} (${u.username})`" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.onDuty.date')" :rules="[{ required: true, message: '必选' }]">
          <el-date-picker v-model="form.duty_date" type="date" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item :label="$t('message.onDuty.dutyType')">
          <el-radio-group v-model="form.duty_type">
            <el-radio label="primary">{{ $t('message.onDuty.primary') }}</el-radio>
            <el-radio label="backup">{{ $t('message.onDuty.backup') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">{{ $t('message.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { onDutyScheduleApi, skillGroupApi } from '/@/api/itsm/index'
import { request } from '/@/utils/service'

const { t } = useI18n()
const loading = ref(false)
const list = ref<any[]>([])
const dialogVisible = ref(false)
const saving = ref(false)
const editingItem = ref<any>(null)
const filterDate = ref('')
const form = ref<any>({ group: null, user: null, duty_date: '', duty_type: 'primary' })
const userOptions = ref<any[]>([])
const groupOptions = ref<any[]>([])

async function loadList() {
  loading.value = true
  try {
    const params: any = {}
    if (filterDate.value) params.duty_date = filterDate.value
    const res = await onDutyScheduleApi.list(params)
    list.value = res?.results || res?.data || []
  } finally { loading.value = false }
}
async function loadOptions() {
  const [uRes, gRes] = await Promise.all([
    request({ url: '/api/system/user/', method: 'get', params: { page_size: 5000 } }),
    skillGroupApi.list(),
  ])
  userOptions.value = (uRes as any).data?.results || (uRes as any).data || []
  groupOptions.value = (gRes as any).results || (gRes as any).data || []
}
function openDialog(item?: any) {
  editingItem.value = item || null
  form.value = item ? { ...item } : { group: null, user: null, duty_date: '', duty_type: 'primary' }
  if (!userOptions.value.length) loadOptions()
  dialogVisible.value = true
}
async function onSave() {
  saving.value = true
  try {
    if (editingItem.value) await onDutyScheduleApi.update(editingItem.value.id, form.value)
    else await onDutyScheduleApi.create(form.value)
    ElMessage.success(t('message.common.saveSuccess'))
    dialogVisible.value = false
    await loadList()
  } catch { ElMessage.error(t('message.common.saveFailed')) }
  saving.value = false
}
async function onDelete(row: any) {
  await ElMessageBox.confirm(t('message.common.deleteConfirm'))
  await onDutyScheduleApi.delete(row.id)
  ElMessage.success(t('message.common.deleted'))
  await loadList()
}
onMounted(() => { loadList(); loadOptions() })
</script>

<style scoped>
.itsm-settings { padding: 4px 0; }
.itsm-settings-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.itsm-settings-title { font-size: 15px; font-weight: 600; color: #303133; }
</style>
