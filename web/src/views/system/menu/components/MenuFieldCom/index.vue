<template>
  <div class="menu-field-com">
    <!-- Toolbar / 工具栏 -->
    <div class="mfc-toolbar">
      <div class="mfc-toolbar-left">
        <span class="mfc-toolbar-title">
          <el-icon size="14"><Grid /></el-icon>
          Column Permission List / 列权限列表
        </span>
      </div>
      <div class="mfc-toolbar-right">
        <el-button v-auth="'column:Match'" type="success" size="small" :disabled="!selectedMenuId" @click="showModelDialog = true">
          <el-icon><Connection /></el-icon> Auto Match / 自动匹配
        </el-button>
        <el-button v-auth="'column:Create'" type="primary" size="small" :disabled="!selectedMenuId" @click="openAddDialog">
          <el-icon><Plus /></el-icon> Add / 新增
        </el-button>
      </div>
    </div>

    <!-- Table / 表格 -->
    <el-table
      ref="tableRef"
      :data="tableData"
      v-loading="loading"
      stripe
      style="width: 100%"
      size="small"
      :empty-text="emptyText"
      max-height="100%"
      class="mfc-table"
    >
      <el-table-column type="index" label="#" width="60" align="center" />
      <el-table-column prop="model" label="Model / 模型" width="150" show-overflow-tooltip>
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.model }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="Display Name / 中文名" min-width="160" show-overflow-tooltip />
      <el-table-column prop="field_name" label="Field Name / 字段名" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <code class="mfc-field-code">{{ row.field_name }}</code>
        </template>
      </el-table-column>
      <el-table-column label="Actions / 操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button v-auth="'column:Update'" size="small" text type="primary" @click="openEditDialog(row)">
            <el-icon><Edit /></el-icon> Edit
          </el-button>
          <el-popconfirm
            title="Confirm delete? / 确认删除?"
            @confirm="handleDelete(row)"
          >
            <template #reference>
              <el-button v-auth="'column:Delete'" size="small" text type="danger">
                <el-icon><Delete /></el-icon> Delete
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add/Edit Dialog / 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? 'Edit Column Permission / 编辑列权限' : 'Add Column Permission / 新增列权限'"
      width="520px"
      :close-on-click-modal="false"
      class="opsflow-dialog"
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px" label-position="top" class="mfc-form">
        <el-form-item label="Model / 模型" prop="model">
          <el-select
            v-model="formData.model"
            filterable
            placeholder="Select model / 选择模型"
            style="width: 100%"
          >
            <el-option
              v-for="m in modelOptions"
              :key="m.value"
              :label="m.label"
              :value="m.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Display Name / 中文名" prop="title">
          <el-input v-model="formData.title" placeholder="Enter display name / 请输入中文名" />
        </el-form-item>
        <el-form-item label="Field Name / 字段名" prop="field_name">
          <el-input v-model="formData.field_name" placeholder="Enter field name / 请输入字段名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">Cancel / 取消</el-button>
          <el-button type="primary" :loading="submitLoading" @click="handleSave">
            {{ isEdit ? 'Update / 更新' : 'Create / 创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Model Selection Dialog / 模型选择弹窗 -->
    <el-dialog
      v-model="showModelDialog"
      title="Select Model / 选择模型"
      width="480px"
      :close-on-click-modal="false"
      class="opsflow-dialog"
    >
      <div class="mfc-model-body">
        <div v-if="selectedModel" class="mfc-model-selected">
          <el-tag closable @close="selectedModel = ''">
            Selected / 已选择: {{ selectedModel }}
          </el-tag>
        </div>
        <div class="mfc-model-list">
          <div
            v-for="(item, index) in allModelData"
            :key="index"
            class="mfc-model-item"
            :class="{ 'mfc-model-active': modelCheckIndex === index }"
            @click="onModelChecked(item, index)"
          >
            <span class="mfc-model-name">{{ item.app }} -- {{ item.title }} ({{ item.key }})</span>
          </div>
          <el-empty v-if="!allModelData.length" description="No models available / 暂无可用模型" :image-size="40" />
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showModelDialog = false">Cancel / 取消</el-button>
          <el-button type="primary" :loading="autoMatchLoading" @click="handleAutomatch">
            Confirm / 确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElForm, FormRules } from 'element-plus';
import { Grid, Plus, Edit, Delete, Connection } from '@element-plus/icons-vue';
import { GetList, AddObj, UpdateObj, DelObj, getModelList, automatchColumnsData } from './api';
import { successNotification, warningNotification } from '/@/utils/message';
import { MenuTreeItemType } from '../../types';

interface ColumnPermissionItem {
  id?: number;
  model: string;
  title: string;
  field_name: string;
  menu?: number;
}

interface ModelOption {
  value: string;
  label: string;
  app?: string;
  key?: string;
  title?: string;
}

const tableData = ref<ColumnPermissionItem[]>([]);
const loading = ref(false);
const selectedMenuId = ref<number | string | null>(null);
const selectedMenuName = ref<string>('');
const dialogVisible = ref(false);
const isEdit = ref(false);
const submitLoading = ref(false);
const editingId = ref<number | null>(null);
const formRef = ref<InstanceType<typeof ElForm>>();
const showModelDialog = ref(false);
const allModelData = ref<any[]>([]);
const modelCheckIndex = ref<number | null>(null);
const selectedModel = ref('');
const autoMatchLoading = ref(false);

const modelOptions = ref<ModelOption[]>([]);

const emptyText = computed(() => {
  if (!selectedMenuId.value) return 'Please select a menu on the left / 请先在左侧选择菜单';
  return 'No data / 暂无数据';
});

const defaultForm: ColumnPermissionItem = {
  model: '',
  title: '',
  field_name: '',
};

let formData = reactive<ColumnPermissionItem>({ ...defaultForm });

const formRules = reactive<FormRules>({
  model: [{ required: true, message: 'Model is required / 必填项', trigger: 'change' }],
  title: [{ required: true, message: 'Display name is required / 必填项', trigger: 'blur' }],
  field_name: [{ required: true, message: 'Field name is required / 必填项', trigger: 'blur' }],
});

/**
 * Fetch column permissions for selected menu / 获取选中菜单的列权限
 */
const fetchData = async () => {
  if (!selectedMenuId.value) {
    tableData.value = [];
    return;
  }
  loading.value = true;
  try {
    const res = await GetList({ menu: selectedMenuId.value } as any);
    if (res?.code === 2000) {
      tableData.value = res.data || [];
    } else if (Array.isArray(res)) {
      tableData.value = res;
    } else {
      tableData.value = [];
    }
  } catch (e) {
    console.error('Failed to load column permissions', e);
    tableData.value = [];
  } finally {
    loading.value = false;
  }
};

/**
 * Fetch model list / 获取模型列表
 */
const fetchModels = async () => {
  try {
    const res = await getModelList();
    if (res?.code === 2000) {
      const items = res.data || [];
      allModelData.value = items;
      modelOptions.value = items.map((item: any) => ({
        value: item.key,
        label: `${item.app} -- ${item.title} (${item.key})`,
        app: item.app,
        key: item.key,
        title: item.title,
      }));
    }
  } catch (e) {
    console.error('Failed to fetch models', e);
  }
};

/**
 * Open add dialog / 打开新增弹窗
 */
const openAddDialog = () => {
  if (!selectedMenuId.value) {
    warningNotification('Please select a menu first! / 请先选择菜单！');
    return;
  }
  isEdit.value = false;
  editingId.value = null;
  Object.assign(formData, { ...defaultForm });
  dialogVisible.value = true;
};

/**
 * Open edit dialog / 打开编辑弹窗
 */
const openEditDialog = (row: ColumnPermissionItem) => {
  isEdit.value = true;
  editingId.value = row.id || null;
  formData.model = row.model;
  formData.title = row.title;
  formData.field_name = row.field_name;
  dialogVisible.value = true;
};

/**
 * Save handler / 保存
 */
const handleSave = async () => {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  submitLoading.value = true;
  try {
    let res: any;
    const payload = { ...formData, menu: selectedMenuId.value };
    if (isEdit.value && editingId.value) {
      res = await UpdateObj({ ...payload, id: editingId.value });
    } else {
      res = await AddObj(payload);
    }
    if (res?.code === 2000) {
      successNotification(res.msg as string);
      dialogVisible.value = false;
      await fetchData();
    }
  } finally {
    submitLoading.value = false;
  }
};

/**
 * Delete handler / 删除
 */
const handleDelete = async (row: ColumnPermissionItem) => {
  try {
    const res = await DelObj(row.id);
    if (res?.code === 2000) {
      successNotification(res.msg as string);
      await fetchData();
    }
  } catch (e) {
    console.error('Delete failed', e);
  }
};

/**
 * Dialog closed / 弹窗关闭
 */
const handleDialogClosed = () => {
  formRef.value?.resetFields();
  Object.assign(formData, { ...defaultForm });
  editingId.value = null;
};

/**
 * Model check / 选择模型
 */
const onModelChecked = (item: any, index: number) => {
  modelCheckIndex.value = index;
  selectedModel.value = item.key || '';
};

/**
 * Auto-match columns / 自动匹配列
 */
const handleAutomatch = async () => {
  if (!selectedMenuId.value || !selectedModel.value) {
    warningNotification('Please select a menu and model! / 请选择菜单和模型表！');
    return;
  }
  autoMatchLoading.value = true;
  try {
    const res = await automatchColumnsData({
      menu: selectedMenuId.value,
      model: selectedModel.value,
      app: allModelData.value[modelCheckIndex.value!]?.app || '',
    });
    if (res?.code === 2000) {
      successNotification('Auto-match successful / 匹配成功');
    }
    showModelDialog.value = false;
    await fetchData();
  } finally {
    autoMatchLoading.value = false;
  }
};

/**
 * External: refresh table when menu selected / 刷新表格
 */
const handleRefreshTable = (record: MenuTreeItemType) => {
  selectedMenuId.value = record.id;
  selectedMenuName.value = record.name || '';
  fetchData();
};

onMounted(() => {
  fetchModels();
});

defineExpose({ handleRefreshTable });
</script>

<style lang="scss" scoped>
@use '../../../../apps/opsflow/styles/opsflow-global' as *;

.menu-field-com {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ===== Toolbar ===== */
.mfc-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.mfc-toolbar-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mfc-toolbar-title {
  font-size: 13px;
  font-weight: 600;
  color: $of-text-primary;
  display: flex;
  align-items: center;
  gap: 6px;
}

.mfc-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== Table ===== */
.mfc-table {
  flex: 1;
  overflow: hidden;
}

.mfc-table :deep(.el-table__header-wrapper) {
  border-radius: 6px 6px 0 0;
}

.mfc-table :deep(th.el-table__cell) {
  background: $of-bg-header;
  color: $of-text-primary;
  font-weight: 600;
  font-size: 12px;
}

.mfc-field-code {
  font-size: 11px;
  background: $of-bg-card;
  padding: 2px 6px;
  border-radius: 4px;
  color: $of-text-secondary;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

/* ===== Form ===== */
.mfc-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: $of-text-primary;
  padding-bottom: 4px;
}

.mfc-form :deep(.el-input__wrapper),
.mfc-form :deep(.el-select .el-input__wrapper) {
  border-radius: 6px;
}

/* ===== Model Dialog ===== */
.mfc-model-body {
  min-height: 200px;
}

.mfc-model-selected {
  margin-bottom: 12px;
}

.mfc-model-list {
  max-height: 300px;
  overflow-y: auto;
  margin-top: 12px;
}

.mfc-model-item {
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: background $of-transition-default, border-color $of-transition-default;
  border: 1px solid transparent;

  &:hover {
    background: $of-bg-light-blue;
    border-color: $of-border-blue;
  }
}

.mfc-model-active {
  background: $of-bg-light-blue;
  border-color: $of-color-primary;
}

.mfc-model-name {
  font-size: 13px;
  color: $of-text-primary;
}
</style>
