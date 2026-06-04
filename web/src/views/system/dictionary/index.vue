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
          字典管理
        </div>
        <div class="sys-card-extra">
          <el-input
            v-model="searchQuery"
            placeholder="搜索字典名称 / 编号"
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
            新增字典
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
          :empty-text="loading ? '加载中...' : '暂无字典数据'"
          row-key="id"
        >
          <el-table-column type="index" label="序号" width="70" align="center">
            <template #default="{ $index }">
              {{ (pagination.page - 1) * pagination.limit + $index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="label" label="字典名称" min-width="140" show-overflow-tooltip />
          <el-table-column prop="value" label="字典编号" min-width="140" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100" align="center">
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
          <el-table-column prop="sort" label="排序" width="80" align="center" />
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="auth('dictionary:Update')"
                size="small"
                text
                type="primary"
                @click="openSubDict(row)"
              >
                <el-icon><Setting /></el-icon>
                字典配置
              </el-button>
              <el-button
                v-if="auth('dictionary:Update')"
                size="small"
                text
                type="primary"
                @click="openEditDialog(row)"
              >
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-popconfirm
                title="确认删除该字典?"
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
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="dict-pagination-wrap">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.limit"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            background
            small
            @current-change="loadData"
            @size-change="loadData"
          />
        </div>
      </div>
    </div>

    <!-- ===== Add / Edit Dialog ===== -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? '编辑字典' : '新增字典'"
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
        <el-form-item label="字典名称" prop="label">
          <el-input
            v-model="dialog.form.label"
            placeholder="请输入字典名称"
            clearable
          />
        </el-form-item>
        <el-form-item label="字典编号" prop="value">
          <div style="width: 100%">
            <el-input
              v-model="dialog.form.value"
              placeholder="请输入字典编号"
              clearable
            />
            <el-alert
              title="使用方法：dictionary('字典编号')"
              type="warning"
              :closable="false"
              show-icon
              style="margin-top: 6px"
            />
          </div>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="dialog.form.status">
            <el-radio :value="true">启用</el-radio>
            <el-radio :value="false">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number
            v-model="dialog.form.sort"
            :min="0"
            :max="999"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.submitting" @click="handleSubmit">
          {{ dialog.isEdit ? '保存' : '确认' }}
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
import { Search, Plus, Notebook, Setting, Edit, Delete } from '@element-plus/icons-vue'
import * as api from './api'
import type { DictItem } from './api'
import { auth } from '/@/utils/authFunction'
import { successMessage } from '/@/utils/message'

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
  label: [{ required: true, message: '字典名称必填项', trigger: 'blur' }],
  value: [{ required: true, message: '字典编号必填项', trigger: 'blur' }],
  status: [{ required: true, message: '状态必填项', trigger: 'change' }],
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
    ElMessage.error(e?.msg || '获取字典列表失败')
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
      successMessage(res.msg || '更新成功')
    } else {
      const res = await api.AddObj(dialog.form)
      successMessage(res.msg || '新增成功')
    }
    dialog.visible = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || '操作失败')
  } finally {
    dialog.submitting = false
  }
}

async function handleDelete(row: DictItem) {
  try {
    const res = await api.DelObj(row.id)
    successMessage(res.msg || '删除成功')
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.msg || '删除失败')
  }
}

async function handleStatusChange(row: DictItem, val: boolean) {
  try {
    const res = await api.UpdateObj({ id: row.id, status: val } as any)
    successMessage(res.msg || '状态更新成功')
    row.status = val
  } catch (e: any) {
    ElMessage.error(e?.msg || '状态更新失败')
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
@use '../styles/system-global' as *;

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
.sys-card-extra {
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
