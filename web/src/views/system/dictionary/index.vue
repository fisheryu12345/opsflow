<template>
  <div class="dict-page sys-page">
    <!-- ===== Main Card ===== -->
    <div class="sys-card dict-fade-in-up">
      <!-- Card header -->
      <div class="sys-card-header">
        <div class="sys-card-title">
          <span class="sys-card-icon">
            <el-icon><Notebook /></el-icon>
          </span>
          {{ $t('message.dictionaryPage.title') }}
        </div>
        <div class="g-card-extra">
          <el-input
            v-model="searchQuery"
            :placeholder="$t('message.dictionaryPage.searchPlaceholder')"
            clearable
            size="default"
            style="width: 260px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button v-if="auth('dictionary:Create')" type="primary" size="default" @click="openAddDialog">
            <el-icon><Plus /></el-icon>
            {{ $t('message.dictionaryPage.add') }}
          </el-button>
        </div>
      </div>

      <!-- Card body: table -->
      <div class="sys-card-body">
        <el-table
          v-loading="loading"
          :data="tableData"
          stripe
          size="small"
          style="width: 100%"
          :empty-text="loading ? $t('message.dictionaryPage.loading') : $t('message.dictionaryPage.empty')"
          row-key="id"
        >
          <el-table-column type="index" :label="$t('message.dictionaryPage.columnIndex')" width="70" align="center">
            <template #default="{ $index }">
              {{ (pagination.page - 1) * pagination.limit + $index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="label" :label="$t('message.dictionaryPage.columnName')" min-width="140" show-overflow-tooltip />
          <el-table-column prop="value" :label="$t('message.dictionaryPage.columnValue')" min-width="140" show-overflow-tooltip />
          <el-table-column prop="status" :label="$t('message.dictionaryPage.columnStatus')" width="100" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.status"
                :active-value="true"
                :inactive-value="false"
                size="small"
                @change="(val: any) => handleStatusChange(row, val)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="sort" :label="$t('message.dictionaryPage.columnSort')" width="80" align="center" />
          <el-table-column :label="$t('message.dictionaryPage.columnActions')" width="240" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="auth('dictionary:Update')"
                size="small"
                text
                type="primary"
                @click="openSubDict(row)"
              >
                <el-icon><Setting /></el-icon>
                {{ $t('message.dictionaryPage.actionConfig') }}
              </el-button>
              <el-button
                v-if="auth('dictionary:Update')"
                size="small"
                text
                type="primary"
                @click="openEditDialog(row)"
              >
                <el-icon><Edit /></el-icon>
                {{ $t('message.dictionaryPage.actionEdit') }}
              </el-button>
              <el-popconfirm
                :title="$t('message.dictionaryPage.confirmDelete')"
                @confirm="handleDelete(row)"
              >
                <template #reference>
                  <el-button
                    v-if="auth('dictionary:Delete')"
                    size="small"
                    text
                    type="danger"
                  >
                    <el-icon><Delete /></el-icon>
                    {{ $t('message.dictionaryPage.actionDelete') }}
                  </el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="dict-pagination-wrap">
          <el-pagination
            v-model:currentPage="pagination.page"
            v-model:pageSize="pagination.limit"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            background
            size="small"
            @update:currentPage="loadData"
            @update:pageSize="loadData"
          />
        </div>
      </div>
    </div>

    <!-- ===== Add / Edit Dialog ===== -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? $t('message.dictionaryPage.editTitle') : $t('message.dictionaryPage.addTitle')"
      width="520px"
      top="8vh"
      destroy-on-close
      class="dict-dialog"
    >
      <el-form
        ref="formRef"
        :model="dialog.form"
        :rules="formRules"
        label-width="100px"
        class="dict-form"
      >
        <el-form-item :label="$t('message.dictionaryPage.formName')" prop="label">
          <el-input
            v-model="dialog.form.label"
            :placeholder="$t('message.dictionaryPage.formNamePlaceholder')"
            clearable
          />
        </el-form-item>
        <el-form-item :label="$t('message.dictionaryPage.formValue')" prop="value">
          <div style="width: 100%">
            <el-input
              v-model="dialog.form.value"
              :placeholder="$t('message.dictionaryPage.formValuePlaceholder')"
              clearable
            />
            <el-alert
              :title="$t('message.dictionaryPage.formValueTips')"
              type="warning"
              :closable="false"
              show-icon
              style="margin-top: 6px"
            />
          </div>
        </el-form-item>
        <el-form-item :label="$t('message.dictionaryPage.formStatus')" prop="status">
          <el-radio-group v-model="dialog.form.status">
            <el-radio :value="true">{{ $t('message.dictionaryPage.formStatusEnable') }}</el-radio>
            <el-radio :value="false">{{ $t('message.dictionaryPage.formStatusDisable') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('message.dictionaryPage.formSort')" prop="sort">
          <el-input-number
            v-model="dialog.form.sort"
            :min="0"
            :max="999"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">{{ $t('message.dictionaryPage.cancel') }}</el-button>
        <el-button type="primary" :loading="dialog.submitting" @click="handleSubmit">
          {{ dialog.isEdit ? $t('message.dictionaryPage.save') : $t('message.dictionaryPage.confirm') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- ===== Sub Dict Drawer (lazy-loaded) ===== -->
    <subDict ref="subDictRef" />
  </div>
</template>

<script setup lang="ts" name="dictionary">
import { ref, reactive, onMounted, defineAsyncComponent } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { Search, Plus, Notebook, Setting, Edit, Delete } from '@element-plus/icons-vue'
import * as api from './api'
import type { DictItem } from './api'
import { auth } from '/@/utils/authFunction'
import { successMessage } from '/@/utils/message'

const { t } = useI18n()

// Lazy-load the sub-dictionary drawer component
const subDict = defineAsyncComponent(() => import('./subDict/index.vue'))
const subDictRef = ref<InstanceType<typeof subDict> | null>(null)

// ===== Table State =====
const loading = ref(false)
const tableData = ref<DictItem[]>([])
const searchQuery = ref('')

const pagination = reactive({
  page: 1,
  limit: 10,
  total: 0,
})

// ===== Dialog State =====
const formRef = ref<FormInstance | null>(null)

const dialog = reactive({
  visible: false,
  isEdit: false,
  submitting: false,
  form: {
    id: null as number | null,
    label: '',
    value: '',
    status: true,
    sort: 1,
  },
})

// ===== Form Rules =====
const formRules = {
  label: [{ required: true, message: t('message.dictionaryPage.nameRequired'), trigger: 'blur' }],
  value: [{ required: true, message: t('message.dictionaryPage.valueRequired'), trigger: 'blur' }],
  status: [{ required: true, message: t('message.dictionaryPage.statusRequired'), trigger: 'change' }],
}

// ===== Data Loading =====
async function loadData() {
  loading.value = true
  try {
    const res = await api.GetList({
      page: pagination.page,
      limit: pagination.limit,
      search: searchQuery.value || undefined,
    })
    tableData.value = res.data || []
    pagination.total = res.total || 0
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.dictionaryPage.fetchFailed'))
    tableData.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

// ===== CRUD Operations =====
function openAddDialog() {
  dialog.isEdit = false
  dialog.form = { id: null, label: '', value: '', status: true, sort: 1 }
  dialog.visible = true
}

function openEditDialog(row: DictItem) {
  dialog.isEdit = true
  dialog.form = {
    id: row.id,
    label: row.label,
    value: row.value,
    status: row.status,
    sort: row.sort,
  }
  dialog.visible = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  dialog.submitting = true
  try {
    if (dialog.isEdit && dialog.form.id) {
      const res = await api.UpdateObj(dialog.form as any)
      successMessage(res.msg || t('message.dictionaryPage.updateSuccess'))
    } else {
      const res = await api.AddObj(dialog.form)
      successMessage(res.msg || t('message.dictionaryPage.createSuccess'))
    }
    dialog.visible = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.dictionaryPage.operationFailed'))
  } finally {
    dialog.submitting = false
  }
}

async function handleDelete(row: DictItem) {
  try {
    const res = await api.DelObj(row.id)
    successMessage(res.msg || t('message.dictionaryPage.deleteSuccess'))
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.dictionaryPage.deleteFailed'))
  }
}

async function handleStatusChange(row: DictItem, val: boolean) {
  try {
    const res = await api.UpdateObj({ id: row.id, status: val } as any)
    successMessage(res.msg || t('message.dictionaryPage.statusUpdateSuccess'))
    row.status = val
  } catch (e: any) {
    ElMessage.error(e?.msg || t('message.dictionaryPage.statusUpdateFailed'))
    // Revert on failure
    await loadData()
  }
}

// ===== Sub Dict Drawer =====
function openSubDict(row: DictItem) {
  subDictRef.value?.open(row.id, row.label)
}

// ===== Init =====
onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

// Fade-in-up animation matching OPSflow style
.dict-fade-in-up {
  animation: dictFadeInUp 0.5s ease both;
}

@keyframes dictFadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dict-page {
  width: 100%;
}

// Card header extra search + button row
.g-card-extra {
  display: flex;
  align-items: center;
  gap: 12px;
}

// Pagination wrapper
.dict-pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

// Dialog form help text
.dict-form :deep(.el-form-item__content) {
  flex-wrap: wrap;
}

// Switch column center alignment
.el-table .el-switch {
  margin: 0 auto;
}
</style>
