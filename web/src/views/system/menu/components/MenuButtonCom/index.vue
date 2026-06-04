<template>
  <div class="menu-button-com">
    <!-- Toolbar / 工具栏 -->
    <div class="mbc-toolbar">
      <div class="mbc-toolbar-left">
        <span class="mbc-toolbar-title">
          <el-icon size="14"><Key /></el-icon>
          Button Permission List / 按钮权限列表
        </span>
      </div>
      <div class="mbc-toolbar-right">
        <el-button v-auth="'btn:Create'" type="primary" size="small" @click="openAddDialog">
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
      class="mbc-table"
    >
      <el-table-column type="index" label="#" width="60" align="center" />
      <el-table-column prop="name" label="Permission Name / 权限名称" min-width="140" show-overflow-tooltip />
      <el-table-column prop="value" label="Permission Value / 权限值" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.value }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="method" label="Method / 请求方式" width="120" align="center">
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
      <el-table-column prop="api" label="API Path / 接口地址" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <code class="mbc-api-code">{{ row.api }}</code>
        </template>
      </el-table-column>
      <el-table-column label="Actions / 操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button v-auth="'btn:Update'" size="small" text type="primary" @click="openEditDialog(row)">
            <el-icon><Edit /></el-icon> Edit
          </el-button>
          <el-popconfirm
            title="Confirm delete? / 确认删除?"
            @confirm="handleDelete(row)"
          >
            <template #reference>
              <el-button v-auth="'btn:Delete'" size="small" text type="danger">
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
      :title="isEdit ? 'Edit Button Permission / 编辑按钮权限' : 'Add Button Permission / 新增按钮权限'"
      width="560px"
      :close-on-click-modal="false"
      class="opsflow-dialog"
      @closed="handleDialogClosed"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="110px" label-position="top" class="mbc-form">
        <el-form-item label="Permission Name / 权限名称" prop="name">
          <el-input v-model="formData.name" placeholder="Enter permission name / 输入权限名称" />
        </el-form-item>
        <el-form-item label="Permission Value / 权限值" prop="value">
          <el-input v-model="formData.value" placeholder="Enter permission value / 输入权限标识" />
        </el-form-item>
        <el-form-item label="Method / 请求方式" prop="method">
          <el-select v-model="formData.method" placeholder="Select method / 选择请求方式" style="width: 100%">
            <el-option :value="0" label="GET" />
            <el-option :value="1" label="POST" />
            <el-option :value="2" label="PUT" />
            <el-option :value="3" label="DELETE" />
          </el-select>
        </el-form-item>
        <el-form-item label="API Path / 接口地址" prop="api">
          <el-select
            v-model="formData.api"
            filterable
            allow-create
            clearable
            placeholder="Select or type API path / 选择或输入接口地址"
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
          <el-button @click="dialogVisible = false">Cancel / 取消</el-button>
          <el-button type="primary" :loading="submitLoading" @click="handleSave">
            {{ isEdit ? 'Update / 更新' : 'Create / 创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from 'vue';
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
  if (!selectedMenu.value) return 'Please select a menu on the left / 请先在左侧选择菜单';
  return 'No data / 暂无数据';
});

const defaultForm: ButtonPermissionItem = {
  name: '',
  value: '',
  method: 0,
  api: '',
};

let formData = reactive<ButtonPermissionItem>({ ...defaultForm });

const formRules = reactive<FormRules>({
  name: [{ required: true, message: 'Permission name is required / 权限名称必填', trigger: 'blur' }],
  value: [{ required: true, message: 'Permission value is required / 权限标识必填', trigger: 'blur' }],
  method: [{ required: true, message: 'Please select method / 请选择请求方式', trigger: 'change' }],
  api: [{ required: true, message: 'API path is required / 接口地址必填', trigger: 'blur' }],
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
    const res = await request({ url: '/swagger.json' });
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
@import '../../../apps/opsflow/styles/opsflow-global';

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
  color: $of-text-primary;
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
  background: $of-bg-header;
  color: $of-text-primary;
  font-weight: 600;
  font-size: 12px;
}

.mbc-api-code {
  font-size: 11px;
  background: $of-bg-card;
  padding: 2px 6px;
  border-radius: 4px;
  color: $of-text-secondary;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

/* ===== Form ===== */
.mbc-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: $of-text-primary;
  padding-bottom: 4px;
}

.mbc-form :deep(.el-input__wrapper),
.mbc-form :deep(.el-select .el-input__wrapper) {
  border-radius: 6px;
}
</style>
