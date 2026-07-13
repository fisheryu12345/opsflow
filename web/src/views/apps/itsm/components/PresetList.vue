<template>
  <div class="preset-list">
    <!-- Toolbar -->
    <div class="itsm-table-toolbar">
      <span class="itsm-table-title">{{ $t('message.preset.title') }}</span>
      <div class="itsm-table-actions">
        <el-select v-model="filterType" :placeholder="$t('message.preset.filterType')" clearable size="small" style="width:140px" @change="loadData">
          <el-option :label="$t('message.preset.type_user_list')" value="user_list" />
          <el-option :label="$t('message.preset.type_role_list')" value="role_list" />
          <el-option :label="$t('message.preset.type_dept_list')" value="dept_list" />
          <el-option :label="$t('message.preset.type_text')" value="text" />
          <el-option :label="$t('message.preset.type_options')" value="options" />
        </el-select>
        <el-input v-model="searchText" :placeholder="$t('message.common.search')" size="small" style="width:200px" clearable @input="loadData" />
        <el-button type="primary" size="small" @click="openCreate">
          <el-icon><Plus /></el-icon> {{ $t('message.common.create') }}
        </el-button>
      </div>
    </div>

    <!-- Table -->
    <el-table :data="list" v-loading="loading" :empty-text="loading ? $t('message.itsmPage.loading') : $t('message.common.empty')" stripe>
      <el-table-column prop="name" :label="$t('message.preset.name')" min-width="160" />
      <el-table-column :label="$t('message.preset.type')" width="120" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="tagType(row.preset_type)">{{ typeLabel(row.preset_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.preset.valuePreview')" min-width="250">
        <template #default="{ row }">
          <span class="preset-value-text">{{ formatValue(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.preset.refCount')" width="100" align="center">
        <template #default="{ row }">
          <el-popover v-if="row.reference_count" placement="right" :width="300" trigger="click">
            <template #reference>
              <el-button link type="primary" size="small" class="preset-ref-count">{{ row.reference_count }}</el-button>
            </template>
            <div class="preset-ref-list">
              <div v-for="(ref, i) in row.referenced_by" :key="i" class="preset-ref-item">
                <el-tag size="small" type="warning" effect="plain">{{ ref.workflow_name }}</el-tag>
                <span class="preset-ref-arrow">→</span>
                <el-tag size="small" type="primary" effect="plain">{{ ref.state_name }}</el-tag>
                <span v-if="ref.field_title" class="preset-ref-field">({{ ref.field_title }})</span>
              </div>
            </div>
          </el-popover>
          <span v-else class="preset-ref-count zero">0</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.itsmPage.colActions')" width="180" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">{{ $t('message.common.edit') }}</el-button>
          <el-button link type="primary" size="small" @click="copyPreset(row)">{{ $t('message.preset.copy') }}</el-button>
          <el-button link type="danger" size="small" @click="deletePreset(row)">{{ $t('message.common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('message.preset.editPreset') : $t('message.preset.createPreset')"
      width="520px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item :label="$t('message.preset.name')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('message.preset.namePlaceholder')" maxlength="128" />
        </el-form-item>
        <el-form-item :label="$t('message.preset.type')" prop="preset_type">
          <el-select v-model="form.preset_type" style="width:100%" :disabled="isEdit" @change="onTypeChange">
            <el-option :label="$t('message.preset.type_user_list')" value="user_list" />
            <el-option :label="$t('message.preset.type_role_list')" value="role_list" />
            <el-option :label="$t('message.preset.type_dept_list')" value="dept_list" />
            <el-option :label="$t('message.preset.type_text')" value="text" />
            <el-option :label="$t('message.preset.type_options')" value="options" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.preset.value')" prop="value">
          <!-- user_list: multi-select user search -->
          <el-select
            v-if="form.preset_type === 'user_list'"
            v-model="form.value"
            multiple filterable
            :placeholder="$t('message.preset.searchUser')"
            style="width:100%"
          >
            <el-option v-for="u in userOptions" :key="u.value" :label="u.label" :value="u.value" />
          </el-select>
          <!-- role_list: tag input -->
          <div v-else-if="form.preset_type === 'role_list'" class="preset-tag-input">
            <el-tag v-for="(r, i) in form.value" :key="i" closable size="small" @close="form.value.splice(i, 1)">{{ r }}</el-tag>
            <el-input v-model="roleInput" size="small" :placeholder="$t('message.preset.rolePlaceholder')" style="width:120px" @keyup.enter="addRole" @blur="addRole" />
          </div>
          <!-- dept_list: tag input -->
          <div v-else-if="form.preset_type === 'dept_list'" class="preset-tag-input">
            <el-tag v-for="(d, i) in form.value" :key="i" closable size="small" @close="form.value.splice(i, 1)">{{ d }}</el-tag>
            <el-input v-model="deptInput" size="small" :placeholder="$t('message.preset.deptPlaceholder')" style="width:140px" @keyup.enter="addDept" @blur="addDept" />
          </div>
          <!-- text: single input -->
          <el-input v-else-if="form.preset_type === 'text'" v-model="form.value" :placeholder="$t('message.preset.textPlaceholder')" />
          <!-- options: key-value table -->
          <div v-else-if="form.preset_type === 'options'" class="preset-options-editor">
            <div v-for="(opt, i) in form.value" :key="i" class="preset-option-row">
              <el-input v-model="opt.label" :placeholder="$t('message.formDesigner.dispName')" size="small" style="width:40%" />
              <el-input v-model="opt.value" :placeholder="$t('message.formDesigner.value')" size="small" style="width:40%" />
              <el-button link type="danger" size="small" @click="form.value.splice(i, 1)"><el-icon><Delete /></el-icon></el-button>
            </div>
            <el-button link type="primary" size="small" @click="form.value.push({ label: '', value: '' })">
              + {{ $t('message.formDesigner.addChoice') }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" @click="submitForm">{{ $t('message.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { presetApi } from '/@/api/itsm/index'
import { request } from '/@/utils/service'
import { Plus, Delete } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{ active: boolean }>()

// Data
const list = ref<any[]>([])
const loading = ref(false)
const filterType = ref('')
const searchText = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const userOptions = ref<any[]>([])

const roleInput = ref('')
const deptInput = ref('')

const form = reactive<any>({
  name: '',
  preset_type: '',
  value: [],
})

const rules = {
  name: [{ required: true, message: () => t('message.preset.nameRequired'), trigger: 'blur' }],
  preset_type: [{ required: true, message: () => t('message.preset.typeRequired'), trigger: 'change' }],
}

// Helpers
function tagType(type: string): string {
  const map: Record<string, string> = { user_list: 'primary', role_list: 'warning', dept_list: 'danger', text: 'success', options: 'info' }
  return map[type] || 'primary'
}

function typeLabel(type: string): string {
  const map: Record<string, string> = {
    user_list: t('message.preset.type_user_list'),
    role_list: t('message.preset.type_role_list'),
    dept_list: t('message.preset.type_dept_list'),
    text: t('message.preset.type_text'),
    options: t('message.preset.type_options'),
  }
  return map[type] || type
}

function formatValue(row: any): string {
  const v = row.value
  if (!v) return '-'
  if (typeof v === 'string') return v
  if (Array.isArray(v)) {
    if (v.length > 0 && typeof v[0] === 'object') {
      return v.map((o: any) => `${o.label}(${o.value})`).join(', ')
    }
    return v.join(', ')
  }
  return String(v)
}

// API
async function loadData() {
  loading.value = true
  try {
    const params: any = {}
    if (filterType.value) params.preset_type = filterType.value
    if (searchText.value) params.search = searchText.value
    const res = await presetApi.list(params)
    list.value = (res as any).data || []
  } finally {
    loading.value = false
  }
}

async function loadUserOptions() {
  try {
    const res = await request({ url: '/api/iam/users/search/', method: 'get', params: { page_size: 500 } })
    userOptions.value = ((res as any).data || []).map((item: any) => ({
      value: item.value,
      label: item.label,
    }))
  } catch { userOptions.value = [] }
}

// Actions
function openCreate() {
  isEdit.value = false
  editingId.value = null
  form.name = ''
  form.preset_type = ''
  form.value = []
  dialogVisible.value = true
}

function openEdit(row: any) {
  isEdit.value = true
  editingId.value = row.id
  form.name = row.name
  form.preset_type = row.preset_type
  form.value = JSON.parse(JSON.stringify(row.value))
  dialogVisible.value = true
}

function onTypeChange() {
  if (form.preset_type === 'user_list' || form.preset_type === 'options') {
    form.value = []
  } else {
    form.value = []
  }
}

function addRole() {
  const v = roleInput.value.trim()
  if (v && !form.value.includes(v)) { form.value.push(v); roleInput.value = '' }
}

function addDept() {
  const v = deptInput.value.trim()
  if (v && !form.value.includes(v)) { form.value.push(v); deptInput.value = '' }
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  try {
    const data = { ...form }
    if (isEdit.value && editingId.value) {
      await presetApi.update(String(editingId.value), data)
      ElMessage.success(t('message.common.saveSuccess'))
    } else {
      await presetApi.create(data)
      ElMessage.success(t('message.common.saveSuccess'))
    }
    dialogVisible.value = false
    loadData()
  } catch { ElMessage.error(t('message.common.saveFailed')) }
}

async function copyPreset(row: any) {
  try {
    await presetApi.create({
      name: row.name + ' (copy)',
      preset_type: row.preset_type,
      value: row.value,
    })
    ElMessage.success(t('message.preset.copied'))
    loadData()
  } catch { ElMessage.error(t('message.common.saveFailed')) }
}

async function deletePreset(row: any) {
  try {
    await ElMessageBox.confirm(t('message.common.deleteConfirm'), t('message.common.delete'), { type: 'warning' })
    await presetApi.delete(String(row.id))
    ElMessage.success(t('message.common.deleted'))
    loadData()
  } catch { /* cancelled */ }
}

onMounted(() => {
  loadData()
  loadUserOptions()
})
</script>

<style scoped lang="scss">
.preset-list {
  .itsm-table-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 8px;
  }
  .itsm-table-title {
    font-size: 16px;
    font-weight: 600;
  }
  .itsm-table-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }
}

.preset-value-text {
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}

.preset-ref-count {
  font-weight: 600;
  color: #409eff;
  &.zero { color: #c0c4cc; font-weight: 400; }
}
.preset-ref-list {
  .preset-ref-item {
    display: flex; align-items: center; gap: 6px; padding: 4px 0;
    font-size: 12px;
    &:not(:last-child) { border-bottom: 1px solid #ebeef5; }
  }
  .preset-ref-arrow { color: #c0c4cc; }
  .preset-ref-field { color: #909399; font-size: 11px; }
}

.preset-tag-input {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 32px;
  padding: 4px 8px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.preset-options-editor {
  .preset-option-row {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 6px;
  }
}
</style>
