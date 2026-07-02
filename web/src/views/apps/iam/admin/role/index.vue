<template>
  <div class="role-page">
    <div class="role-card">
      <!-- Search bar + Add button -->
      <div class="role-search">
        <el-input
          v-model="searchForm.name"
          :placeholder="$t('message.rolePage.inputPlaceholder')"
          clearable
          size="default"
          :prefix-icon="Search"
          style="width:220px"
          @input="handleSearch"
        />
        <el-select
          v-model="searchForm.status"
          :placeholder="$t('message.rolePage.all')"
          clearable
          size="default"
          style="width:120px"
          @change="handleSearch"
        >
          <el-option :label="$t('message.rolePage.enabled')" :value="true" />
          <el-option :label="$t('message.rolePage.disabled')" :value="false" />
        </el-select>
        <el-button size="default" :icon="Refresh" @click="handleReset">{{ $t('message.rolePage.reset') }}</el-button>
        <span style="flex:1" />
        <el-button type="primary" :icon="Plus" size="default" @click="handleAdd">{{ $t('message.rolePage.addRole') }}</el-button>
      </div>

      <!-- Table -->
      <div class="role-table-wrap">
        <el-table
          :data="tableData"
          v-loading="loading"
          stripe
          size="small"
          style="width:100%"
          @sort-change="handleSortChange"
        >
          <el-table-column type="index" :label="$t('message.rolePage.index')" width="50" align="center" />
          <el-table-column prop="name" :label="$t('message.rolePage.roleName')" min-width="150" sortable="custom" show-overflow-tooltip />
          <el-table-column prop="key" :label="$t('message.rolePage.roleKey')" min-width="140" show-overflow-tooltip />
          <el-table-column prop="sort" :label="$t('message.rolePage.sort')" width="70" sortable="custom" align="center" />
          <el-table-column :label="$t('message.rolePage.status')" width="80" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.status"
                :active-value="true"
                :inactive-value="false"
                size="small"
                @change="() => handleStatusChange(row)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="update_datetime" :label="$t('message.rolePage.updateTime')" min-width="155" sortable="custom" show-overflow-tooltip />
          <el-table-column prop="create_datetime" :label="$t('message.rolePage.createTime')" min-width="155" sortable="custom" show-overflow-tooltip />
          <el-table-column :label="$t('message.rolePage.actions')" width="240" fixed="right" align="center">
            <template #default="{ row }">
              <el-button text size="small" style="padding:0 4px" @click="handleView(row)">{{ $t('message.rolePage.view') }}</el-button>
              <el-button text size="small" style="padding:0 4px" @click="handleEdit(row)">{{ $t('message.rolePage.edit') }}</el-button>
              <el-button text type="danger" size="small" style="padding:0 4px" @click="handleDelete(row)">{{ $t('message.rolePage.delete') }}</el-button>
              <el-button text size="small" style="padding:0 4px" @click="handlePermissionOpen(row)">{{ $t('message.rolePage.permission') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Pagination -->
      <div class="role-pagination">
        <el-pagination
          v-model:currentPage="pagination.page"
          v-model:pageSize="pagination.limit"
          :total="pagination.total"
          :page-sizes="[15,30,50,100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          small
          @update:pageSize="handleSizeChange"
          @update:currentPage="handleCurrentChange"
        />
      </div>
    </div>

    <!-- ===== View Dialog ===== -->
    <el-dialog v-model="viewDialogVisible" :title="$t('message.rolePage.viewRole')" width="560px" :close-on-click-modal="false" class="opsflow-dialog">
      <el-form label-width="100px" disabled>
        <el-form-item :label="$t('message.rolePage.roleName')">{{ viewForm.name }}</el-form-item>
        <el-form-item :label="$t('message.rolePage.roleKey')"><span>{{ viewForm['key'] }}</span></el-form-item>
        <el-form-item :label="$t('message.rolePage.sort')">{{ viewForm.sort }}</el-form-item>
        <el-form-item :label="$t('message.rolePage.status')">
          <el-tag :type="viewForm.status ? 'success' : 'danger'" effect="plain" round>
            {{ viewForm.status ? $t('message.rolePage.enabled') : $t('message.rolePage.disabled') }}
          </el-tag>
        </el-form-item>
        <el-form-item :label="$t('message.rolePage.createTime')">{{ viewForm.create_datetime }}</el-form-item>
        <el-form-item :label="$t('message.rolePage.updateTime')">{{ viewForm.update_datetime }}</el-form-item>
      </el-form>
    </el-dialog>

    <!-- ===== Add / Edit Dialog ===== -->
    <el-dialog
      v-model="editDialogVisible"
      :title="editMode === 'add' ? $t('message.rolePage.addRole') : $t('message.rolePage.editRole')"
      width="560px"
      :close-on-click-modal="false"
      :before-close="handleEditDialogClose"
      class="opsflow-dialog"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editFormRules" label-width="100px">
        <el-form-item :label="$t('message.rolePage.roleName')" prop="name">
          <el-input v-model="editForm.name" :placeholder="$t('message.rolePage.roleNamePlaceholder')" maxlength="50" />
        </el-form-item>
        <el-form-item :label="$t('message.rolePage.roleKey')" prop="key">
          <el-input v-model="editForm.key" :placeholder="$t('message.rolePage.keyPlaceholder')" maxlength="50" />
        </el-form-item>
        <el-form-item :label="$t('message.rolePage.sort')" prop="sort">
          <el-input-number v-model="editForm.sort" :min="0" />
        </el-form-item>
        <el-form-item :label="$t('message.rolePage.status')" prop="status">
          <el-radio-group v-model="editForm.status">
            <el-radio :value="true">{{ $t('message.rolePage.enabled') }}</el-radio>
            <el-radio :value="false">{{ $t('message.rolePage.disabled') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleEditDialogClose">{{ $t('message.rolePage.cancel') }}</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleEditSubmit">{{ $t('message.rolePage.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- ===== Permission Panel ===== -->
    <RolePermissionPanel
      v-model="permissionDrawerVisible"
      :roleId="permissionRoleId"
      :roleName="permissionRoleName"
      @closed="permissionRoleId = 0"
    />
  </div>
</template>

<script setup lang="ts" name="role">
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessageBox, ElMessage } from 'element-plus';
import { Plus, Search, Refresh } from '@element-plus/icons-vue';
import { GetList, GetObj, AddObj, UpdateObj, DelObj } from './api';

import { successMessage } from '/@/utils/message';
import RolePermissionPanel from './components/RolePermissionPanel.vue';

/* ===================== Types ===================== */
interface RoleItem {
  id: number | string;
  name: string;
  key: string;
  sort: number;
  status: boolean;
  update_datetime: string;
  create_datetime: string;
  [key: string]: any;
}

/* ===================== i18n ===================== */
const { t } = useI18n();

/* ===================== State ===================== */
const loading = ref(false);
const tableData = ref<RoleItem[]>([]);

const searchForm = reactive({ name: '', status: undefined as boolean | string | undefined });

const pagination = reactive({ page: 1, limit: 15, total: 0, ordering: '' });

/* ===================== View Dialog ===================== */
const viewDialogVisible = ref(false);
const viewForm = reactive<Partial<RoleItem>>({});

/* ===================== Edit Dialog ===================== */
const editDialogVisible = ref(false);
const editMode = ref<'add' | 'edit'>('add');
const editLoading = ref(false);
const editFormRef = ref();
const editForm = reactive<Partial<RoleItem>>({ name: '', key: '', sort: 1, status: true, id: undefined });
const editFormRules = {
  name: [{ required: true, message: t('message.rolePage.nameRequired'), trigger: 'blur' }],
  key: [{ required: true, message: t('message.rolePage.keyRequired'), trigger: 'blur' }],
  sort: [{ required: true, message: t('message.rolePage.sortRequired'), trigger: 'blur' }],
};

/* ===================== Permission Drawer ===================== */
const permissionDrawerVisible = ref(false);
const permissionRoleId = ref<number | string>(0);
const permissionRoleName = ref('');

/* ===================== API Methods ===================== */
const fetchData = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: pagination.page, limit: pagination.limit };
    if (searchForm.name) params.name = searchForm.name;
    if (searchForm.status !== undefined && searchForm.status !== '') params.status = searchForm.status;
    if (pagination.ordering) params.ordering = pagination.ordering;
    const res: any = await GetList(params);
    if (res?.code === 2000) {
      tableData.value = res.data || [];
      pagination.total = res.total || 0;
    } else {
      tableData.value = [];
    }
  } catch { tableData.value = []; }
  finally { loading.value = false; }
};

/* ===================== Handlers ===================== */
const handleSearch = () => { pagination.page = 1; fetchData(); };
const handleReset = () => { searchForm.name = ''; searchForm.status = undefined; pagination.page = 1; fetchData(); };
const handleSortChange = ({ prop, order }: { prop?: string; order?: string }) => {
  pagination.ordering = prop && order ? (order === 'ascending' ? prop : `-${prop}`) : '';
  fetchData();
};
const handleSizeChange = (val: number) => { pagination.limit = val; pagination.page = 1; fetchData(); };
const handleCurrentChange = (val: number) => { pagination.page = val; fetchData(); };

const handleStatusChange = async (row: RoleItem) => {
  try {
    const res: any = await UpdateObj(row);
    if (res?.code === 2000) successMessage(res.msg || t('message.rolePage.updateSuccess'));
  } catch { /* noop */ }
};

const handleView = (row: RoleItem) => { Object.assign(viewForm, row); viewDialogVisible.value = true; };

const handleAdd = () => {
  editMode.value = 'add';
  Object.assign(editForm, { id: undefined, name: '', key: '', sort: 1, status: true });
  editDialogVisible.value = true;
};

const handleEdit = async (row: RoleItem) => {
  editMode.value = 'edit';
  try {
    const res: any = await GetObj(row.id);
    if (res?.code === 2000 && res.data) {
      const d = res.data;
      Object.assign(editForm, { id: d.id, name: d.name, key: d.key, sort: d.sort, status: d.status });
      editDialogVisible.value = true;
    }
  } catch { ElMessage.error(t('message.rolePage.fetchRoleFailed')); }
};

const handleDelete = (row: RoleItem) => {
  ElMessageBox.confirm(t('message.rolePage.confirmDelete', { name: row.name }), t('message.rolePage.confirmTitle'), {
    confirmButtonText: t('message.rolePage.deleteBtn'), cancelButtonText: t('message.rolePage.cancelBtn'), type: 'warning',
  }).then(async () => {
    try {
      const res: any = await DelObj(row.id);
      if (res?.code === 2000) { successMessage(t('message.rolePage.deleteSuccess')); fetchData(); }
    } catch { /* noop */ }
  }).catch(() => {});
};

const handleEditDialogClose = () => { editDialogVisible.value = false; };

const handleEditSubmit = async () => {
  if (!editFormRef.value) return;
  try { await editFormRef.value.validate(); } catch { return; }
  editLoading.value = true;
  try {
    const res: any = editMode.value === 'add' ? await AddObj(editForm) : await UpdateObj(editForm);
    if (res?.code === 2000) {
      successMessage(res.msg || t('message.rolePage.saveSuccess'));
      editDialogVisible.value = false;
      fetchData();
    }
  } finally { editLoading.value = false; }
};

const handlePermissionOpen = (row: RoleItem) => {
  permissionRoleId.value = row.id;
  permissionRoleName.value = row.name;
  permissionDrawerVisible.value = true;
};

/* ===================== Lifecycle ===================== */
onMounted(() => { fetchData(); });
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;

.role-page {
  width: 100%;
  height: 100%;
}

// ===== Card =====
.role-card {
  background: #fff;
  border-radius: $g-radius-card;
  box-shadow: $g-shadow-card;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 230px);
  overflow: hidden;
}

// ===== Search bar =====
.role-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  border-bottom: 1px solid $g-border-light;
  flex-shrink: 0;
}

// ===== Table wrapper =====
.role-table-wrap {
  flex: 1;
  overflow: auto;
  padding: 0;
}
.role-table-wrap :deep(.el-table) {
  border: none;
}
.role-table-wrap :deep(.el-table th.el-table__cell) {
  background: $g-bg-header;
  color: $g-text-primary;
  font-weight: 600;
  font-size: 12px;
}

// ===== Pagination =====
.role-pagination {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid $g-border-light;
}
</style>
