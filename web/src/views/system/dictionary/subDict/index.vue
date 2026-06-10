<template>
  <!-- 子字典抽屉 / Sub-dictionary drawer -->
  <el-drawer
    v-model="drawerVisible"
    size="70%"
    direction="rtl"
    destroy-on-close
    :title="$t('message.dictionaryPage.subDictTitle')"
    :before-close="handleClose"
    class="subdict-drawer"
  >
    <!-- 搜索栏 / Search bar -->
    <div class="subdict-search">
      <el-form :model="searchForm" inline>
        <el-form-item :label="$t('message.dictionaryPage.subDictSearchLabel')">
          <el-input v-model="searchForm.label" :placeholder="$t('message.dictionaryPage.subDictSearchPlaceholder')" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="small" @click="handleSearch">{{ $t('message.dictionaryPage.subDictSearch') }}</el-button>
          <el-button size="small" @click="handleReset">{{ $t('message.dictionaryPage.subDictReset') }}</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 工具栏 / Toolbar -->
    <div class="subdict-toolbar">
      <el-button type="primary" size="small" icon="Plus" @click="openAddDialog">{{ $t('message.dictionaryPage.subDictAdd') }}</el-button>
    </div>

    <!-- 数据表格 / Data table -->
    <el-table
      :data="tableData"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
      size="small"
    >
      <el-table-column type="index" :label="$t('message.dictionaryPage.subDictColumnIndex')" width="70" align="center">
        <template #default="{ $index }">
          {{ ((pagination.currentPage - 1) * pagination.pageSize) + $index + 1 }}
        </template>
      </el-table-column>
      <el-table-column prop="label" :label="$t('message.dictionaryPage.subDictColumnName')" min-width="120" show-overflow-tooltip />
      <el-table-column prop="value" :label="$t('message.dictionaryPage.subDictColumnValue')" min-width="120" show-overflow-tooltip />
      <el-table-column prop="type" :label="$t('message.dictionaryPage.subDictColumnValueType')" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small">{{ typeMap[row.type] || row.type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" :label="$t('message.dictionaryPage.subDictColumnStatus')" width="80" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.status"
            @change="(val: boolean) => handleStatusChange(row, val)"
            inline-prompt
            active-text=""
            inactive-text=""
            style="--el-switch-on-color: var(--el-color-primary); --el-switch-off-color: #dcdfe6"
          />
        </template>
      </el-table-column>
      <el-table-column prop="sort" :label="$t('message.dictionaryPage.subDictColumnSort')" width="70" align="center" />
      <el-table-column prop="color" :label="$t('message.dictionaryPage.subDictColumnColor')" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.color" :type="row.color" effect="plain" size="small">{{ row.color }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.dictionaryPage.subDictColumnActions')" width="160" fixed="right" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openEditDialog(row)">{{ $t('message.dictionaryPage.subDictEdit') }}</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)">{{ $t('message.dictionaryPage.subDictDelete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 / Pagination -->
    <div class="subdict-pagination">
      <el-pagination
        v-model:currentPage="pagination.currentPage"
        v-model:pageSize="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @update:currentPage="getList"
        @update:pageSize="getList"
      />
    </div>
  </el-drawer>

  <!-- 新增/编辑弹窗 / Add/Edit dialog -->
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? $t('message.dictionaryPage.subDictEditTitle') : $t('message.dictionaryPage.subDictAddTitle')"
    width="500px"
    append-to-body
    destroy-on-close
    class="of-dialog"
  >
    <el-form ref="formRef" :model="formData" :rules="formRules" label-position="top" size="default">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item :label="$t('message.dictionaryPage.subDictFormName')" prop="label">
            <el-input v-model="formData.label" :placeholder="$t('message.dictionaryPage.subDictFormNamePlaceholder')" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="$t('message.dictionaryPage.subDictFormValue')" prop="value">
            <el-input v-model="formData.value" :placeholder="$t('message.dictionaryPage.subDictFormValuePlaceholder')" clearable />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item :label="$t('message.dictionaryPage.subDictFormValueType')" prop="type">
            <el-select v-model="formData.type" :placeholder="$t('message.dictionaryPage.subDictFormValueTypePlaceholder')" style="width:100%">
              <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="$t('message.dictionaryPage.subDictFormStatus')" prop="status">
            <el-radio-group v-model="formData.status">
              <el-radio :value="true">{{ $t('message.dictionaryPage.subDictFormStatusEnable') }}</el-radio>
              <el-radio :value="false">{{ $t('message.dictionaryPage.subDictFormStatusDisable') }}</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item :label="$t('message.dictionaryPage.subDictFormSort')" prop="sort">
            <el-input-number v-model="formData.sort" :min="0" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item :label="$t('message.dictionaryPage.subDictFormColor')" prop="color">
            <el-select v-model="formData.color" :placeholder="$t('message.dictionaryPage.subDictFormColorPlaceholder')" clearable style="width:100%">
              <el-option v-for="item in colorOptions" :key="item.value" :label="item.label" :value="item.value">
                <el-tag :type="item.value" size="small">{{ item.label }}</el-tag>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <template #footer>
      <span class="of-dialog-footer">
        <el-button size="small" @click="dialogVisible = false">{{ $t('message.dictionaryPage.subDictCancel') }}</el-button>
        <el-button size="small" type="primary" @click="handleSubmit" :loading="submitLoading">{{ $t('message.dictionaryPage.subDictConfirm') }}</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
import type { FormInstance } from 'element-plus';
import { ElMessageBox } from 'element-plus';
import { successMessage } from '/@/utils/message';
import * as api from './api';
import type { DictItem } from './api';

/* ---------- 数据值类型映射 / Type display map ---------- */
const typeMap: Record<number, string> = {
  0: 'text', 1: 'number', 2: 'date', 3: 'datetime', 4: 'time', 5: 'file', 6: 'boolean', 7: 'images',
};
const typeOptions = Object.entries(typeMap).map(([value, label]) => ({ value: Number(value), label }));

const colorOptions = [
  { label: 'success', value: 'success' as const }, { label: 'primary', value: 'primary' as const },
  { label: 'info', value: 'info' as const }, { label: 'danger', value: 'danger' as const }, { label: 'warning', value: 'warning' as const },
];

/* ---------- Drawer state ---------- */
const drawerVisible = ref(false);
const parentId = ref<number | null>(null);

/* ---------- Search ---------- */
const searchForm = reactive({ label: '' });

/* ---------- Table ---------- */
const tableData = ref<DictItem[]>([]);
const loading = ref(false);
const pagination = reactive({ currentPage: 1, pageSize: 15, total: 0 });

/* ---------- Dialog ---------- */
const dialogVisible = ref(false);
const isEdit = ref(false);
const submitLoading = ref(false);
const formRef = ref<FormInstance>();
const formData = reactive<DictItem>({ label: '', value: '', type: 0, status: true, sort: 1, color: '' });

const formRules = {
  label: [{ required: true, message: t('message.dictionaryPage.subDictNameRequired'), trigger: 'blur' }],
  value: [{ required: true, message: t('message.dictionaryPage.subDictValueRequired'), trigger: 'blur' }],
  type: [{ required: true, message: t('message.dictionaryPage.subDictValueTypeRequired'), trigger: 'change' }],
};

/* ---------- API ---------- */
async function getList() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: pagination.currentPage, limit: pagination.pageSize };
    if (searchForm.label) params.label = searchForm.label;
    if (parentId.value) params.parent = parentId.value;
    const res: any = await api.GetList(params);
    tableData.value = res.data || [];
    pagination.total = res.total || 0;
  } finally { loading.value = false; }
}

function handleSearch() { pagination.currentPage = 1; getList(); }
function handleReset() { searchForm.label = ''; pagination.currentPage = 1; getList(); }

function handleStatusChange(row: DictItem, val: boolean) {
  api.UpdateObj({ id: row.id, status: val }).then((res: any) => {
    successMessage(res.msg || t('message.dictionaryPage.subDictUpdateSuccess'));
    row.status = val;
  });
}

function openAddDialog() {
  isEdit.value = false;
  Object.assign(formData, { label: '', value: '', type: 0, status: true, sort: 1, color: '' });
  dialogVisible.value = true;
}

function openEditDialog(row: DictItem) {
  isEdit.value = true;
  Object.assign(formData, { id: row.id, label: row.label, value: row.value, type: row.type, status: row.status, sort: row.sort, color: row.color || '' });
  dialogVisible.value = true;
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitLoading.value = true;
  try {
    const data = { ...formData } as any;
    if (parentId.value) data.parent = parentId.value;
    const res: any = isEdit.value ? await api.UpdateObj(data) : await api.AddObj(data);
    successMessage(res.msg || (isEdit.value ? t('message.dictionaryPage.subDictUpdateSuccess') : t('message.dictionaryPage.subDictCreateSuccess')));
    dialogVisible.value = false;
    getList();
  } finally { submitLoading.value = false; }
}

function handleDelete(row: DictItem) {
  ElMessageBox.confirm(t('message.dictionaryPage.subDictConfirmDelete'), t('message.dictionaryPage.subDictConfirmTitle'), {
    confirmButtonText: t('message.dictionaryPage.subDictConfirmBtn'), cancelButtonText: t('message.dictionaryPage.subDictCancelBtn'), type: 'warning',
  }).then(() => {
    api.DelObj(row.id!).then((res: any) => { successMessage(res.msg || t('message.dictionaryPage.subDictDeleteSuccess')); getList(); });
  }).catch(() => {});
}

function handleClose(done: () => void) {
  ElMessageBox.confirm(t('message.dictionaryPage.subDictCloseConfirm'), {
    confirmButtonText: t('message.dictionaryPage.subDictCloseConfirmBtn'), cancelButtonText: t('message.dictionaryPage.subDictCloseCancelBtn'), type: 'warning',
  }).then(() => done()).catch(() => {});
}

function open(parentIdVal: number, _label?: string) {
  parentId.value = parentIdVal;
  drawerVisible.value = true;
  pagination.currentPage = 1;
  getList();
}

defineExpose({ drawer: drawerVisible, open, doRefresh: () => { pagination.currentPage = 1; getList(); } });
</script>

<style scoped>
.subdict-search {
  padding: 0 0 12px;
}
.subdict-toolbar {
  padding-bottom: 12px;
}
.subdict-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}
</style>

<style>
/* Dialog styling */
.of-dialog .el-dialog__header {
  padding: 14px 20px;
  margin: 0;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
}
.of-dialog .el-dialog__body {
  padding: 20px;
}
.of-dialog .el-dialog__body .el-form-item {
  margin-bottom: 16px;
}
.of-dialog .el-dialog__footer {
  padding: 10px 20px;
  border-top: 1px solid #e4e7ed;
}
.of-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
