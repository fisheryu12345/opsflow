<template>
  <div class="sys-page role-page">
    <!-- ===== Stats Cards ===== -->
    <div class="role-stats-row g-fade-in-up">
      <div v-for="card in statCards" :key="card.label" class="role-stat-card">
        <div class="role-stat-icon" :style="{ background: card.bg }">
          <el-icon :size="20"><component :is="card.icon" /></el-icon>
        </div>
        <div class="role-stat-body">
          <div class="role-stat-value">{{ card.value }}</div>
          <div class="role-stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- ===== Main Card ===== -->
    <div class="sys-card g-fade-in-up" style="animation-delay:0.08s">
      <div class="sys-card-header">
        <div class="sys-card-title">
          <span class="sys-card-icon">
            <el-icon :size="16"><User /></el-icon>
          </span>
          <span>{{ $t('message.rolePage.roleManagement') }}</span>
        </div>
        <div class="sys-card-extra">
          <el-button type="primary" :icon="Plus" @click="handleAdd">{{ $t('message.rolePage.addRole') }}</el-button>
        </div>
      </div>

      <div class="sys-card-body">
        <!-- Toolbar: Search -->
        <div class="role-toolbar">
          <el-form :model="searchForm" inline size="default">
            <el-form-item :label="$t('message.rolePage.roleName')">
              <el-input v-model="searchForm.name" :placeholder="$t('message.rolePage.inputPlaceholder')" clearable style="width:180px" @keyup.enter="handleSearch" />
            </el-form-item>
            <el-form-item :label="$t('message.rolePage.status')">
              <el-select v-model="searchForm.status" :placeholder="$t('message.rolePage.all')" clearable style="width:110px" @change="handleSearch">
                <el-option :label="$t('message.rolePage.enabled')" :value="true" />
                <el-option :label="$t('message.rolePage.disabled')" :value="false" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="small" @click="handleSearch">
                <el-icon><Search /></el-icon> {{ $t('message.rolePage.search') }}
              </el-button>
              <el-button size="small" @click="handleReset">
                <el-icon><Refresh /></el-icon> {{ $t('message.rolePage.reset') }}
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- Table -->
        <el-table
          :data="tableData"
          v-loading="loading"
          stripe
          style="width:100%"
          @sort-change="handleSortChange"
        >
          <el-table-column type="index" :label="$t('message.rolePage.index')" width="65" align="center" />
          <el-table-column v-if="colPerm('name','is_query')" prop="name" :label="$t('message.rolePage.roleName')" min-width="140" sortable="custom" />
          <el-table-column v-if="colPerm('key','is_query')" prop="key" :label="$t('message.rolePage.roleKey')" min-width="140" />
          <el-table-column v-if="colPerm('sort','is_query')" prop="sort" :label="$t('message.rolePage.sort')" width="80" sortable="custom" align="center" />
          <el-table-column v-if="colPerm('status','is_query')" :label="$t('message.rolePage.status')" width="100" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.status"
                :active-value="true"
                :inactive-value="false"
                @change="() => handleStatusChange(row)"
              />
            </template>
          </el-table-column>
          <el-table-column v-if="colPerm('update_datetime','is_query')" prop="update_datetime" :label="$t('message.rolePage.updateTime')" min-width="170" sortable="custom" />
          <el-table-column v-if="colPerm('create_datetime','is_query')" prop="create_datetime" :label="$t('message.rolePage.createTime')" min-width="170" sortable="custom" />
          <el-table-column :label="$t('message.rolePage.actions')" :width="actionColWidth" fixed="right" align="center">
            <template #default="{ row }">
              <el-button text size="small" style="padding:0 4px" @click="handleView(row)">{{ $t('message.rolePage.view') }}</el-button>
              <el-button text size="small" style="padding:0 4px" @click="handleEdit(row)">{{ $t('message.rolePage.edit') }}</el-button>
              <el-button text type="danger" size="small" style="padding:0 4px" @click="handleDelete(row)">{{ $t('message.rolePage.delete') }}</el-button>
              <el-button text size="small" style="padding:0 4px" @click="handlePermissionOpen(row)">{{ $t('message.rolePage.permission') }}</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="role-pagination">
          <el-pagination
            v-model:currentPage="pagination.page"
            v-model:pageSize="pagination.limit"
            :total="pagination.total"
            :page-sizes="[15,30,50,100]"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @update:pageSize="handleSizeChange"
            @update:currentPage="handleCurrentChange"
          />
        </div>
      </div>
    </div>

    <!-- ===== View Dialog ===== -->
    <el-dialog v-model="viewDialogVisible" :title="$t('message.rolePage.viewRole')" width="560px" :close-on-click-modal="false" class="opsflow-dialog">
      <el-form label-width="100px" disabled>
        <el-form-item :label="$t('message.rolePage.roleName')">{{ viewForm.name }}</el-form-item>
        <el-form-item :label="$t('message.rolePage.roleKey')">{{ viewForm.key }}</el-form-item>
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
        <el-form-item
          v-if="(editMode==='add' && colPerm('name','is_create')) || (editMode==='edit' && colPerm('name','is_update'))"
          :label="$t('message.rolePage.roleName')" prop="name"
        >
          <el-input v-model="editForm.name" :placeholder="$t('message.rolePage.roleNamePlaceholder')" maxlength="50" />
        </el-form-item>
        <el-form-item
          v-if="(editMode==='add' && colPerm('key','is_create')) || (editMode==='edit' && colPerm('key','is_update'))"
          :label="$t('message.rolePage.roleKey')" prop="key"
        >
          <el-input v-model="editForm.key" :placeholder="$t('message.rolePage.keyPlaceholder')" maxlength="50" />
        </el-form-item>
        <el-form-item
          v-if="(editMode==='add' && colPerm('sort','is_create')) || (editMode==='edit' && colPerm('sort','is_update'))"
          :label="$t('message.rolePage.sort')" prop="sort"
        >
          <el-input-number v-model="editForm.sort" :min="0" />
        </el-form-item>
        <el-form-item
          v-if="(editMode==='add' && colPerm('status','is_create')) || (editMode==='edit' && colPerm('status','is_update'))"
          :label="$t('message.rolePage.status')" prop="status"
        >
          <el-radio-group v-model="editForm.status">
            <el-radio :value="true">{{ $t('message.rolePage.enabled') }}</el-radio>
            <el-radio :value="false">{{ $t('message.rolePage.disabled') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button  @click="handleEditDialogClose">{{ $t('message.rolePage.cancel') }}</el-button>
        <el-button  type="primary" :loading="editLoading" @click="handleEditSubmit">{{ $t('message.rolePage.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- ===== Permission Drawer ===== -->
    <PermissionComNew
      v-if="permissionDrawerVisible"
      v-model:drawerVisible="permissionDrawerVisible"
      :roleId="permissionRoleId"
      :roleName="permissionRoleName"
    />
  </div>
</template>

<script setup lang="ts" name="role">
import { ref, reactive, computed, onMounted, markRaw } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessageBox, ElMessage } from 'element-plus';
import { Plus, Search, Refresh, User, Tickets, Check, Close } from '@element-plus/icons-vue';
import { GetList, GetObj, AddObj, UpdateObj, DelObj, GetPermission } from './api';

import { successMessage } from '/@/utils/message';
import PermissionComNew from './components/PermissionComNew/index.vue';

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
interface ColumnPermItem {
  field_name: string;
  is_query: boolean;
  is_create: boolean;
  is_update: boolean;
}

/* ===================== i18n ===================== */
const { t } = useI18n();

/* ===================== Stats ===================== */
const statCards = computed(() => [
  { label: t('message.rolePage.statTotal'), value: pagination.total, icon: markRaw(Tickets), bg: 'linear-gradient(135deg, #409eff, #337ecc)' },
  { label: t('message.rolePage.statEnabled'), value: tableData.value.filter(r => r.status).length, icon: markRaw(Check), bg: 'linear-gradient(135deg, #67c23a, #409eff)' },
  { label: t('message.rolePage.statDisabled'), value: tableData.value.filter(r => !r.status).length, icon: markRaw(Close), bg: 'linear-gradient(135deg, #f56c6c, #e6a23c)' },
  { label: t('message.rolePage.statCurrent'), value: '---', icon: markRaw(User), bg: 'linear-gradient(135deg, #909399, #606266)' },
]);

/* ===================== State ===================== */
const loading = ref(false);
const tableData = ref<RoleItem[]>([]);

const searchForm = reactive({ name: '', status: undefined as boolean | string | undefined });

const pagination = reactive({ page: 1, limit: 15, total: 0, ordering: '' });

/* ===================== Column Permissions ===================== */
const columnPerms = ref<ColumnPermItem[]>([]);
const colPerm = (field: string, type: 'is_query' | 'is_create' | 'is_update'): boolean => {
  const item = columnPerms.value.find(i => i.field_name === field);
  return item ? item[type] : true;
};

/* ===================== Action Column Width ===================== */
const actionColWidth = computed(() => {
  let count = 1; // 查看
  if (auth('role:Update')) count++;
  if (auth('role:Delete')) count++;
  if (auth('role:Permission')) count++;
  return 60 + count * 55;
});

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

const loadColumnPermissions = async () => {
  try {
    const res: any = await GetPermission();
    if (res?.code === 2000 && Array.isArray(res.data)) columnPerms.value = res.data;
  } catch { /* noop */ }
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
onMounted(async () => {
  await loadColumnPermissions();
  fetchData();
});
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;

.role-page {
  width: 100%;
}

// ===== Stats Cards =====
.role-stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.role-stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #fff;
  border-radius: $g-radius;
  padding: 16px 18px;
  box-shadow: $g-shadow-card;
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: default;

  &:hover {
    transform: translateY(-2px);
    box-shadow: $g-shadow-hover;
  }
}

.role-stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
}

.role-stat-body {
  flex: 1;
  min-width: 0;
}

.role-stat-value {
  font-size: 22px;
  font-weight: 700;
  color: $g-text-primary;
  line-height: 1.2;
}

.role-stat-label {
  font-size: 13px;
  color: $g-text-secondary;
  margin-top: 2px;
}

// ===== Toolbar =====
.role-toolbar {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid $g-border-light;

  :deep(.el-form--inline .el-form-item) {
    margin-right: 14px;
    margin-bottom: 0;
  }
}

// ===== Pagination =====
.role-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  margin-top: 4px;
  border-top: 1px solid $g-border-light;
}
</style>
