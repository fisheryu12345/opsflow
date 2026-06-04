<template>
  <div class="sys-page role-page">
    <!-- ===== Stats Cards ===== -->
    <div class="role-stats-row of-fade-in-up">
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
    <div class="sys-card of-fade-in-up" style="animation-delay:0.08s">
      <div class="sys-card-header">
        <div class="sys-card-title">
          <span class="sys-card-icon">
            <el-icon :size="16"><User /></el-icon>
          </span>
          <span>角色管理</span>
        </div>
        <div class="sys-card-extra">
          <el-button v-if="auth('role:Create')" type="primary" :icon="Plus" @click="handleAdd">新增角色</el-button>
        </div>
      </div>

      <div class="sys-card-body">
        <!-- Toolbar: Search -->
        <div class="role-toolbar">
          <el-form :model="searchForm" inline size="default">
            <el-form-item label="角色名称">
              <el-input v-model="searchForm.name" placeholder="请输入" clearable style="width:180px" @keyup.enter="handleSearch" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="searchForm.status" placeholder="全部" clearable style="width:110px" @change="handleSearch">
                <el-option v-for="item in statusDict" :key="String(item.value)" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearch">
                <el-icon><Search /></el-icon> 查询
              </el-button>
              <el-button @click="handleReset">重置</el-button>
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
          <el-table-column type="index" label="序号" width="65" align="center" />
          <el-table-column v-if="colPerm('name','is_query')" prop="name" label="角色名称" min-width="140" sortable="custom" />
          <el-table-column v-if="colPerm('key','is_query')" prop="key" label="权限标识" min-width="140" />
          <el-table-column v-if="colPerm('sort','is_query')" prop="sort" label="排序" width="80" sortable="custom" align="center" />
          <el-table-column v-if="colPerm('status','is_query')" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.status"
                :active-value="true"
                :inactive-value="false"
                @change="() => handleStatusChange(row)"
              />
            </template>
          </el-table-column>
          <el-table-column v-if="colPerm('update_datetime','is_query')" prop="update_datetime" label="更新时间" min-width="170" sortable="custom" />
          <el-table-column v-if="colPerm('create_datetime','is_query')" prop="create_datetime" label="创建时间" min-width="170" sortable="custom" />
          <el-table-column label="操作" :width="actionColWidth" fixed="right" align="center">
            <template #default="{ row }">
              <el-button text type="primary" size="small" style="padding:0 4px" @click="handleView(row)">查看</el-button>
              <el-button v-if="auth('role:Update')" text type="primary" size="small" style="padding:0 4px" @click="handleEdit(row)">编辑</el-button>
              <el-button v-if="auth('role:Delete')" text type="danger" size="small" style="padding:0 4px" @click="handleDelete(row)">删除</el-button>
              <el-button v-if="auth('role:Permission')" text type="primary" size="small" style="padding:0 4px" @click="handlePermissionOpen(row)">权限</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="role-pagination">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.limit"
            :total="pagination.total"
            :page-sizes="[15,30,50,100]"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>

    <!-- ===== View Dialog ===== -->
    <el-dialog v-model="viewDialogVisible" title="查看角色" width="560px" :close-on-click-modal="false" class="opsflow-dialog">
      <el-form label-width="100px" disabled>
        <el-form-item label="角色名称">{{ viewForm.name }}</el-form-item>
        <el-form-item label="权限标识">{{ viewForm.key }}</el-form-item>
        <el-form-item label="排序">{{ viewForm.sort }}</el-form-item>
        <el-form-item label="状态">
          <el-tag :type="viewForm.status ? 'success' : 'danger'" effect="plain" round>
            {{ viewForm.status ? '启用' : '禁用' }}
          </el-tag>
        </el-form-item>
        <el-form-item label="创建时间">{{ viewForm.create_datetime }}</el-form-item>
        <el-form-item label="更新时间">{{ viewForm.update_datetime }}</el-form-item>
      </el-form>
    </el-dialog>

    <!-- ===== Add / Edit Dialog ===== -->
    <el-dialog
      v-model="editDialogVisible"
      :title="editMode === 'add' ? '新增角色' : '编辑角色'"
      width="560px"
      :close-on-click-modal="false"
      :before-close="handleEditDialogClose"
      class="opsflow-dialog"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editFormRules" label-width="100px">
        <el-form-item
          v-if="(editMode==='add' && colPerm('name','is_create')) || (editMode==='edit' && colPerm('name','is_update'))"
          label="角色名称" prop="name"
        >
          <el-input v-model="editForm.name" placeholder="请输入角色名称" maxlength="50" />
        </el-form-item>
        <el-form-item
          v-if="(editMode==='add' && colPerm('key','is_create')) || (editMode==='edit' && colPerm('key','is_update'))"
          label="权限标识" prop="key"
        >
          <el-input v-model="editForm.key" placeholder="输入唯一标识" maxlength="50" />
        </el-form-item>
        <el-form-item
          v-if="(editMode==='add' && colPerm('sort','is_create')) || (editMode==='edit' && colPerm('sort','is_update'))"
          label="排序" prop="sort"
        >
          <el-input-number v-model="editForm.sort" :min="0" />
        </el-form-item>
        <el-form-item
          v-if="(editMode==='add' && colPerm('status','is_create')) || (editMode==='edit' && colPerm('status','is_update'))"
          label="状态" prop="status"
        >
          <el-radio-group v-model="editForm.status">
            <el-radio v-for="item in statusDict" :key="String(item.value)" :value="item.value">
              {{ item.label }}
            </el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleEditDialogClose">取消</el-button>
        <el-button type="primary" :loading="editLoading" round @click="handleEditSubmit">确定</el-button>
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
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessageBox, ElMessage } from 'element-plus';
import { Plus, Search, User, Tickets, Check, Close } from '@element-plus/icons-vue';
import { GetList, GetObj, AddObj, UpdateObj, DelObj, GetPermission } from './api';
import { dictionary } from '/@/utils/dictionary';
import { auth } from '/@/utils/authFunction';
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

/* ===================== Stats ===================== */
const statCards = computed(() => [
  { label: '角色总数', value: pagination.total, icon: Tickets, bg: 'linear-gradient(135deg, #409eff, #337ecc)' },
  { label: '已启用', value: tableData.value.filter(r => r.status).length, icon: Check, bg: 'linear-gradient(135deg, #67c23a, #409eff)' },
  { label: '已禁用', value: tableData.value.filter(r => !r.status).length, icon: Close, bg: 'linear-gradient(135deg, #f56c6c, #e6a23c)' },
  { label: '当前查询', value: '---', icon: User, bg: 'linear-gradient(135deg, #909399, #606266)' },
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

/* ===================== Dictionary ===================== */
const statusDict = computed(() => dictionary('button_status_bool') || []);

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
  name: [{ required: true, message: '角色名称必填', trigger: 'blur' }],
  key: [{ required: true, message: '权限标识必填', trigger: 'blur' }],
  sort: [{ required: true, message: '排序必填', trigger: 'blur' }],
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
    if (res?.code === 2000) successMessage(res.msg || '更新成功');
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
  } catch { ElMessage.error('获取角色信息失败'); }
};

const handleDelete = (row: RoleItem) => {
  ElMessageBox.confirm(`确认删除角色「${row.name}」？`, '确认', {
    confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
  }).then(async () => {
    try {
      const res: any = await DelObj(row.id);
      if (res?.code === 2000) { successMessage('删除成功'); fetchData(); }
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
      successMessage(res.msg || '保存成功');
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
@use '../styles/system-global' as *;

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
  border-radius: $sys-radius;
  padding: 16px 18px;
  box-shadow: $sys-shadow-card;
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: default;

  &:hover {
    transform: translateY(-2px);
    box-shadow: $sys-shadow-hover;
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
  color: $sys-text-primary;
  line-height: 1.2;
}

.role-stat-label {
  font-size: 13px;
  color: $sys-text-secondary;
  margin-top: 2px;
}

// ===== Toolbar =====
.role-toolbar {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid $sys-border-light;

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
  border-top: 1px solid $sys-border-light;
}
</style>
