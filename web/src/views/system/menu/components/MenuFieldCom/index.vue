<template>
  <div class="menu-field-com">
    <!-- Toolbar / 工具栏 -->
    <div class="mfc-toolbar">
      <div class="mfc-toolbar-left">
        <span class="mfc-toolbar-title">
          <el-icon size="14"><Grid /></el-icon>
          {{ $t('message.menuPage.colPermList') }}
        </span>
      </div>
      <div class="mfc-toolbar-right">
        <el-button v-auth="'column:Match'" type="success" size="small" :disabled="!selectedMenuId" @click="showModelDialog = true">
          <el-icon><Connection /></el-icon> {{ $t('message.menuPage.colAutoMatch') }}
        </el-button>
        <el-button v-auth="'column:Create'" type="primary" size="small" :disabled="!selectedMenuId" @click="openAddDialog">
          <el-icon><Plus /></el-icon> {{ $t('message.menuPage.colAdd') }}
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
      <el-table-column prop="model" :label="$t('message.menuPage.colModel')" width="150" show-overflow-tooltip>
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.model }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" :label="$t('message.menuPage.colDisplayName')" min-width="160" show-overflow-tooltip />
      <el-table-column prop="field_name" :label="$t('message.menuPage.colFieldName')" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <code class="mfc-field-code">{{ row.field_name }}</code>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.menuPage.colActions')" width="160" fixed="right">
        <template #default="{ row }">
          <el-button v-auth="'column:Update'" size="small" text type="primary" @click="openEditDialog(row)">
            <el-icon><Edit /></el-icon> {{ $t('message.menuPage.colEdit') }}
          </el-button>
          <el-popconfirm
            :title="$t('message.menuPage.colConfirmDel')"
            @confirm="handleDelete(row)"
          >
            <template #reference>
              <el-button v-auth="'column:Delete'" size="small" text type="danger">
                <el-icon><Delete /></el-icon> {{ $t('message.menuPage.colDelete') }}
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add/Edit Dialog / 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('message.menuPage.colEditPerm') : $t('message.menuPage.colAddPerm')"
      width="520px"
      :close-on-click-modal="false"
      class="opsflow-dialog"
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px" label-position="top" class="mfc-form">
        <el-form-item :label="$t('message.menuPage.colModelLabel')" prop="model">
          <el-select
            v-model="formData.model"
            filterable
            :placeholder="$t('message.menuPage.colSelectModel')"
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
        <el-form-item :label="$t('message.menuPage.colDisplayNameLabel')" prop="title">
          <el-input v-model="formData.title" :placeholder="$t('message.menuPage.colDisplayNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('message.menuPage.colFieldNameLabel')" prop="field_name">
          <el-input v-model="formData.field_name" :placeholder="$t('message.menuPage.colFieldNamePlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">{{ $t('message.menuPage.colCancel') }}</el-button>
          <el-button type="primary" :loading="submitLoading" @click="handleSave">
            {{ isEdit ? $t('message.menuPage.colUpdate') : $t('message.menuPage.colCreate') }}
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Model Selection Dialog / 模型选择弹窗 -->
    <el-dialog
      v-model="showModelDialog"
      :title="$t('message.menuPage.colSelectModelTitle')"
      width="480px"
      :close-on-click-modal="false"
      class="opsflow-dialog"
    >
      <div class="mfc-model-body">
        <div v-if="selectedModel" class="mfc-model-selected">
          <el-tag closable @close="selectedModel = ''">
            {{ $t('message.menuPage.colSelected') }}: {{ selectedModel }}
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
          <el-empty v-if="!allModelData.length" :description="$t('message.menuPage.colNoModels')" :image-size="40" />
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showModelDialog = false">{{ $t('message.menuPage.colCancel') }}</el-button>
          <el-button type="primary" :loading="autoMatchLoading" @click="handleAutomatch">
            {{ $t('message.menuPage.colConfirm') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElForm, FormRules } from 'element-plus';
import { Grid, Plus, Edit, Delete, Connection } from '@element-plus/icons-vue';
import { GetList, AddObj, UpdateObj, DelObj, getModelList, automatchColumnsData } from './api';
import { successNotification, warningNotification } from '/@/utils/message';
import { MenuTreeItemType } from '../../types';

const { t } = useI18n();

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
  if (!selectedMenuId.value) return t('message.menuPage.colSelectMenuFirst');
  return t('message.menuPage.colNoData');
});

const defaultForm: ColumnPermissionItem = {
  model: '',
  title: '',
  field_name: '',
};

let formData = reactive<ColumnPermissionItem>({ ...defaultForm });

const formRules = reactive<FormRules>({
  model: [{ required: true, message: t('message.menuPage.colModelRequired'), trigger: 'change' }],
  title: [{ required: true, message: t('message.menuPage.colDispNameRequired'), trigger: 'blur' }],
  field_name: [{ required: true, message: t('message.menuPage.colFieldNameRequired'), trigger: 'blur' }],
});

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

const openAddDialog = () => {
  if (!selectedMenuId.value) {
    warningNotification(t('message.menuPage.selectMenuWarning'));
    return;
  }
  isEdit.value = false;
  editingId.value = null;
  Object.assign(formData, { ...defaultForm });
  dialogVisible.value = true;
};

const openEditDialog = (row: ColumnPermissionItem) => {
  isEdit.value = true;
  editingId.value = row.id || null;
  formData.model = row.model;
  formData.title = row.title;
  formData.field_name = row.field_name;
  dialogVisible.value = true;
};

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

const handleDialogClosed = () => {
  formRef.value?.resetFields();
  Object.assign(formData, { ...defaultForm });
  editingId.value = null;
};

const onModelChecked = (item: any, index: number) => {
  modelCheckIndex.value = index;
  selectedModel.value = item.key || '';
};

const handleAutomatch = async () => {
  if (!selectedMenuId.value || !selectedModel.value) {
    warningNotification(t('message.menuPage.colSelectMenuAndModel'));
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
      successNotification(t('message.menuPage.colAutoMatchSuccess'));
    }
    showModelDialog.value = false;
    await fetchData();
  } finally {
    autoMatchLoading.value = false;
  }
};

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
@use '../../../../../styles/opsflow-global' as *;

.menu-field-com {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

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
