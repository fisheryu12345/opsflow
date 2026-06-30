<template>
  <div class="menu-button-com">
    <!-- Toolbar / 工具栏 -->
    <div class="mbc-toolbar">
      <div class="mbc-toolbar-left">
        <span class="mbc-toolbar-title">
          <el-icon size="14"><Key /></el-icon>
          {{ $t('message.menuPage.btnPermList') }}
        </span>
      </div>
      <div class="mbc-toolbar-right">
        <el-button type="primary" size="small" @click="openAddDialog">
          <el-icon><Plus /></el-icon> {{ $t('message.menuPage.btnAdd') }}
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
      class="mbc-table"
    >
      <el-table-column type="index" label="#" width="60" align="center" />
      <el-table-column prop="name" :label="$t('message.menuPage.permName')" min-width="140" show-overflow-tooltip />
      <el-table-column prop="value" :label="$t('message.menuPage.permValue')" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.value }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="method" :label="$t('message.menuPage.method')" width="120" align="center">
        <template #default="{ row }">
          <el-tag
            :type="methodTagType(row.method)"
            size="small"
            effect="dark"
          >
            {{ methodLabel(row.method) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="api" :label="$t('message.menuPage.apiPath')" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <code class="mbc-api-code">{{ row.api }}</code>
        </template>
      </el-table-column>
      <el-table-column :label="$t('message.menuPage.actions')" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text @click="openEditDialog(row)">
            <el-icon><Edit /></el-icon> {{ $t('message.menuPage.edit') }}
          </el-button>
          <el-popconfirm
            :title="$t('message.menuPage.confirmDelPerm')"
            @confirm="handleDelete(row)"
          >
            <template #reference>
              <el-button size="small" text type="danger">
                <el-icon><Delete /></el-icon> {{ $t('message.menuPage.delete') }}
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add/Edit Dialog / 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('message.menuPage.editPerm') : $t('message.menuPage.addPerm')"
      width="560px"
      :close-on-click-modal="false"
      class="opsflow-dialog"
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="110px" label-position="top" class="mbc-form">
        <el-form-item :label="$t('message.menuPage.permName')" prop="name">
          <el-input v-model="formData.name" :placeholder="$t('message.menuPage.permNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('message.menuPage.permValue')" prop="value">
          <el-input v-model="formData.value" :placeholder="$t('message.menuPage.permValuePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('message.menuPage.method')" prop="method">
          <el-select v-model="formData.method" :placeholder="$t('message.menuPage.methodPlaceholder')" style="width: 100%">
            <el-option :value="0" label="GET" />
            <el-option :value="1" label="POST" />
            <el-option :value="2" label="PUT" />
            <el-option :value="3" label="DELETE" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.menuPage.apiPath')" prop="api">
          <el-select
            v-model="formData.api"
            filterable
            allow-create
            clearable
            :placeholder="$t('message.menuPage.apiPathPlaceholder')"
            style="width: 100%"
          >
            <el-option
              v-for="path in apiPaths"
              :key="path"
              :label="path"
              :value="path"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">{{ $t('message.common.cancel') }}</el-button>
          <el-button type="primary" :loading="submitLoading" @click="handleSave">
            {{ isEdit ? $t('message.menuPage.update') : $t('message.menuPage.create') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElForm, ElMessageBox, FormRules } from 'element-plus';
import { Key, Plus, Edit, Delete } from '@element-plus/icons-vue';
import { GetList, AddObj, UpdateObj, DelObj } from './api';
import { request } from '/@/utils/service';
import { successNotification, warningNotification } from '/@/utils/message';
import { MenuTreeItemType } from '../../types';

interface ButtonPermissionItem {
  id?: number;
  name: string;
  value: string;
  method: number;
  api: string;
  menu?: number;
}

const { t } = useI18n();

const tableData = ref<ButtonPermissionItem[]>([]);
const loading = ref(false);
const selectedMenu = ref<MenuTreeItemType | null>(null);
const dialogVisible = ref(false);
const isEdit = ref(false);
const submitLoading = ref(false);
const editingId = ref<number | null>(null);
const formRef = ref<InstanceType<typeof ElForm>>();
const apiPaths = ref<string[]>([]);

const emptyText = computed(() => {
  if (!selectedMenu.value) return t('message.menuPage.selectMenuFirst');
  return t('message.menuPage.noData');
});

const defaultForm: ButtonPermissionItem = {
  name: '',
  value: '',
  method: 0,
  api: '',
};

let formData = reactive<ButtonPermissionItem>({ ...defaultForm });

const formRules = reactive<FormRules>({
  name: [{ required: true, message: t('message.menuPage.permNameRequired'), trigger: 'blur' }],
  value: [{ required: true, message: t('message.menuPage.permValueRequired'), trigger: 'blur' }],
  method: [{ required: true, message: t('message.menuPage.methodRequired'), trigger: 'change' }],
  api: [{ required: true, message: t('message.menuPage.apiPathRequired'), trigger: 'blur' }],
});

const methodLabel = (method: number): string => {
  const map: Record<number, string> = { 0: 'GET', 1: 'POST', 2: 'PUT', 3: 'DELETE' };
  return map[method] || 'GET';
};

const methodTagType = (method: number): string => {
  const map: Record<number, string> = { 0: '', 1: 'success', 2: 'warning', 3: 'danger' };
  return map[method] || '';
};

/**
 * Fetch button permissions for selected menu / 获取选中菜单的按钮权限
 */
const fetchData = async () => {
  if (!selectedMenu.value?.id) {
    tableData.value = [];
    return;
  }
  loading.value = true;
  try {
    const res = await GetList({ menu: selectedMenu.value.id } as any);
    if (res?.code === 2000) {
      tableData.value = res.data || [];
    } else if (Array.isArray(res)) {
      tableData.value = res;
    } else {
      tableData.value = [];
    }
  } catch (e) {
    console.error('Failed to load button permissions', e);
    tableData.value = [];
  } finally {
    loading.value = false;
  }
};

/**
 * Fetch API paths from swagger / 从swagger获取接口地址列表
 */
const fetchApiPaths = async () => {
  try {
    const res = await request({ url: '/api/schema/' });
    if (res?.paths) {
      apiPaths.value = Object.keys(res.paths);
    }
  } catch (e) {
    console.error('Failed to fetch API paths', e);
  }
};

/**
 * Open add dialog / 打开新增弹窗
 */
const openAddDialog = () => {
  if (!selectedMenu.value?.id) {
    warningNotification(t('message.menuPage.selectMenuWarning'));
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
const openEditDialog = (row: ButtonPermissionItem) => {
  isEdit.value = true;
  editingId.value = row.id || null;
  formData.name = row.name;
  formData.value = row.value;
  formData.method = row.method;
  formData.api = row.api;
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
    const payload = { ...formData, menu: selectedMenu.value!.id };
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
const handleDelete = async (row: ButtonPermissionItem) => {
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
 * External: refresh table when menu selected / 刷新表格
 */
const handleRefreshTable = (record: MenuTreeItemType) => {
  selectedMenu.value = record;
  fetchData();
};

onMounted(() => {
  fetchApiPaths();
});

defineExpose({ handleRefreshTable });
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.menu-button-com {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ===== Toolbar ===== */
.mbc-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.mbc-toolbar-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mbc-toolbar-title {
  font-size: 13px;
  font-weight: 600;
  color: $g-text-primary;
  display: flex;
  align-items: center;
  gap: 6px;
}

.mbc-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== Table ===== */
.mbc-table {
  flex: 1;
  overflow: hidden;
}

.mbc-table :deep(.el-table__header-wrapper) {
  border-radius: 6px 6px 0 0;
}

.mbc-table :deep(th.el-table__cell) {
  background: $g-bg-header;
  color: $g-text-primary;
  font-weight: 600;
  font-size: 12px;
}

.mbc-api-code {
  font-size: 11px;
  background: $g-bg-card;
  padding: 2px 6px;
  border-radius: 4px;
  color: $g-text-secondary;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

/* ===== Form ===== */
.mbc-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: $g-text-primary;
  padding-bottom: 4px;
}

.mbc-form :deep(.el-input__wrapper),
.mbc-form :deep(.el-select .el-input__wrapper) {
  border-radius: 6px;
}
</style>
