<template>
  <div class="user-page">
    <!-- Stats Cards -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="never" class="stats-card stats-total">
          <div class="stats-value">{{ stats.totalUsers }}</div>
          <div class="stats-label">用户总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stats-card stats-active">
          <div class="stats-value">{{ stats.activeUsers }}</div>
          <div class="stats-label">活跃用户</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stats-card stats-inactive">
          <div class="stats-value">{{ stats.inactiveUsers }}</div>
          <div class="stats-label">锁定用户</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stats-card stats-dept">
          <div class="stats-value">{{ stats.deptUserCount }}</div>
          <div class="stats-label">{{ currentDeptName || '当前部门用户' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Main Content: Tree + Table -->
    <el-row class="main-row" :gutter="10">
      <!-- Left: Department Tree -->
      <el-col :span="5" class="left-col">
        <el-card shadow="never" class="tree-card">
          <template #header>
            <div class="tree-header">
              <span class="tree-header-title">部门列表</span>
              <el-tooltip content="点击部门节点筛选用户" placement="right">
                <el-icon><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
          </template>
          <el-input
            v-model="filterText"
            placeholder="搜索部门名称"
            size="default"
            clearable
            class="tree-filter"
          />
          <el-tree
            ref="treeRef"
            :data="deptTreeData"
            :props="treeProps"
            :filter-node-method="filterNode"
            node-key="id"
            highlight-current
            default-expand-all
            @node-click="onTreeNodeClick"
          >
            <template #default="{ data }">
              <span class="tree-node-label">
                <SvgIcon name="iconfont icon-shouye" />&nbsp;{{ data.name }}
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- Right: User Table -->
      <el-col :span="19" class="right-col">
        <el-card shadow="never" class="table-card">
          <!-- Toolbar -->
          <div class="table-toolbar">
            <div class="toolbar-left">
              <el-button
                v-if="auth('user:Create')"
                type="primary"
                @click="openAddDialog"
              >
                新增
              </el-button>
              <el-button
                v-if="auth('user:Export')"
                @click="handleExport"
              >
                导出
              </el-button>
              <importExcel
                v-if="auth('user:Import')"
                api="api/system/user/"
              />
            </div>
            <div class="toolbar-right">
              <el-form :inline="true" :model="searchForm" class="search-form">
                <el-form-item>
                  <el-input
                    v-model="searchForm.username"
                    placeholder="账号"
                    clearable
                    @keyup.enter="handleSearch"
                  />
                </el-form-item>
                <el-form-item>
                  <el-input
                    v-model="searchForm.name"
                    placeholder="姓名"
                    clearable
                    @keyup.enter="handleSearch"
                  />
                </el-form-item>
                <el-form-item>
                  <el-input
                    v-model="searchForm.mobile"
                    placeholder="手机号"
                    clearable
                    @keyup.enter="handleSearch"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="handleSearch">搜索</el-button>
                  <el-button @click="resetSearch">重置</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>

          <!-- Table -->
          <el-table
            :data="tableData"
            v-loading="loading"
            stripe
            border
            style="width: 100%"
            row-key="id"
          >
            <el-table-column type="index" label="#" width="55" align="center" fixed />
            <el-table-column prop="username" label="账号" min-width="120" show-overflow-tooltip />
            <el-table-column prop="name" label="姓名" min-width="100" show-overflow-tooltip />
            <el-table-column label="部门" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.dept_name || row.dept?.name || '' }}
              </template>
            </el-table-column>
            <el-table-column label="角色" min-width="160">
              <template #default="{ row }">
                <el-tag
                  v-for="r in resolveRoles(row)"
                  :key="r.id || r"
                  size="small"
                  class="role-tag"
                >
                  {{ r.name || r }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="mobile" label="手机号" width="130" />
            <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
            <el-table-column label="性别" width="70" align="center">
              <template #default="{ row }">
                {{ getDictLabel('gender', row.gender) }}
              </template>
            </el-table-column>
            <el-table-column label="用户类型" width="90" align="center">
              <template #default="{ row }">
                {{ getDictLabel('user_type', row.user_type) }}
              </template>
            </el-table-column>
            <el-table-column label="锁定" width="80" align="center">
              <template #default="{ row }">
                <el-switch
                  :model-value="Boolean(row.is_active)"
                  :loading="row._switchLoading"
                  @change="(val) => handleActiveChange(row, val)"
                  inline-prompt
                  active-text="是"
                  inactive-text="否"
                  style="--el-switch-on-color: var(--el-color-primary); --el-switch-off-color: #dcdfe6"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="auth('user:Update')"
                  type="primary"
                  link
                  size="small"
                  @click="openEditDialog(row)"
                >
                  编辑
                </el-button>
                <el-button
                  v-if="auth('user:Delete')"
                  type="danger"
                  link
                  size="small"
                  @click="handleDelete(row)"
                >
                  删除
                </el-button>
                <el-button
                  v-if="auth('user:ResetPassword')"
                  type="warning"
                  link
                  size="small"
                  @click="openResetPwdDialog(row)"
                >
                  重设密码
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- Pagination -->
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="limit"
              :total="total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              background
              @size-change="getList"
              @current-change="getList"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '新增用户' : '编辑用户'"
      width="700px"
      :close-on-click-modal="false"
      :destroy-on-close="true"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="90px"
        label-position="right"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="账号" prop="username">
              <el-input v-model="formData.username" placeholder="请输入账号" maxlength="150" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名" prop="name">
              <el-input v-model="formData.name" placeholder="请输入姓名" maxlength="50" />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="dialogType === 'add'">
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="formData.password"
                type="password"
                show-password
                placeholder="请输入密码"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="部门" prop="dept">
              <el-tree-select
                v-model="formData.dept"
                :data="deptSelectData"
                :props="deptSelectProps"
                placeholder="请选择部门"
                filterable
                check-strictly
                clearable
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色" prop="role">
              <el-select
                v-model="formData.role"
                multiple
                filterable
                placeholder="请选择角色"
                style="width: 100%"
              >
                <el-option
                  v-for="item in roleOptions"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号" prop="mobile">
              <el-input v-model="formData.mobile" placeholder="请输入手机号" maxlength="20" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="formData.email" placeholder="请输入邮箱" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="性别" prop="gender">
              <el-select v-model="formData.gender" placeholder="请选择性别" style="width: 100%">
                <el-option
                  v-for="item in genderDict"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="锁定" prop="is_active">
              <el-switch v-model="formData.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Reset Password Dialog -->
    <el-dialog
      v-model="resetPwdVisible"
      title="重设密码"
      width="420px"
      :close-on-click-modal="false"
      :destroy-on-close="true"
      @close="resetResetPwdForm"
    >
      <el-form ref="resetPwdFormRef" :model="resetPwdForm" :rules="resetPwdRules" label-width="80px">
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="resetPwdForm.newPassword"
            type="password"
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="newPassword2">
          <el-input
            v-model="resetPwdForm.newPassword2"
            type="password"
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="resetPwdVisible = false">取消</el-button>
          <el-button type="primary" :loading="resetPwdLoading" @click="handleResetPwdSubmit">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup name="user">
import { ref, reactive, onMounted, watch, computed, provide } from 'vue';
import XEUtils from 'xe-utils';
import { ElMessageBox } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import { Md5 } from 'ts-md5';
import SvgIcon from '/@/components/SvgIcon/index.vue';
import importExcel from '/@/components/importExcel/index.vue';
import { auth } from '/@/utils/authFunction';
import { dictionary } from '/@/utils/dictionary';
import { successMessage, successNotification } from '/@/utils/message';
import { request } from '/@/utils/service';
import { SystemConfigStore } from '/@/stores/systemConfig';
import * as api from './api';

// ============================================================
// Types
// ============================================================
interface DeptTreeNode {
  id: number;
  name: string;
  parent?: number;
  status?: boolean;
  children?: DeptTreeNode[];
}

interface UserRecord {
  id: number;
  username: string;
  name: string;
  dept?: { id: number; name: string };
  dept_name?: string;
  role?: number[];
  role_info?: { id: number; name: string }[];
  mobile?: string;
  email?: string;
  gender?: number;
  user_type?: number;
  is_active?: boolean;
  avatar?: string;
  _switchLoading?: boolean;
  [key: string]: any;
}

interface RoleItem {
  id: number;
  name: string;
  [key: string]: any;
}

interface StatsState {
  totalUsers: number;
  activeUsers: number;
  inactiveUsers: number;
  deptUserCount: number;
}

// ============================================================
// Provide refreshView for importExcel component
// ============================================================
provide('refreshView', () => {
  getList();
});

// ============================================================
// Store / Config
// ============================================================
const systemConfigStore = SystemConfigStore();
const defaultPassword = computed(() => {
  return systemConfigStore.systemConfig?.['base.default_password'] || '123456';
});

// ============================================================
// Dictionary helpers
// ============================================================
const genderDict = computed(() => (dictionary('gender') as any[]) || []);

function getDictLabel(dictName: string, value: number | string | undefined): string {
  if (value === undefined || value === null) return '';
  const items = dictionary(dictName) as any[];
  if (!items) return String(value);
  const found = items.find((d: any) => d.value === value);
  return found ? found.label : String(value);
}

// ============================================================
// Roles & Depts options
// ============================================================
const roleOptions = ref<RoleItem[]>([]);
const deptSelectData = ref<any[]>([]);

async function fetchRoleOptions() {
  try {
    const res: any = await request({
      url: '/api/system/role/',
      method: 'get',
    });
    if (res?.code === 2000) {
      roleOptions.value = res.data || [];
    }
  } catch (e) {
    console.error('Failed to fetch roles', e);
  }
}

async function fetchDeptSelectData() {
  try {
    const res: any = await request({
      url: '/api/system/dept/all_dept/',
      method: 'get',
    });
    if (res?.code === 2000 && Array.isArray(res.data)) {
      deptSelectData.value = res.data;
    }
  } catch (e) {
    console.error('Failed to fetch dept select data', e);
  }
}

// ============================================================
// Stats
// ============================================================
const stats = reactive<StatsState>({
  totalUsers: 0,
  activeUsers: 0,
  inactiveUsers: 0,
  deptUserCount: 0,
});

function computeStats(data: UserRecord[]) {
  let active = 0;
  let inactive = 0;
  data.forEach((u) => {
    if (u.is_active) active++;
    else inactive++;
  });
  stats.totalUsers = data.length;
  stats.activeUsers = active;
  stats.inactiveUsers = inactive;
}

// ============================================================
// Department Tree
// ============================================================
const filterText = ref('');
const treeRef = ref<any>(null);
const deptTreeData = ref<DeptTreeNode[]>([]);
const currentDeptId = ref<number | null>(null);
const currentDeptName = ref('');

const treeProps = {
  children: 'children',
  label: 'name',
};

watch(filterText, (val) => {
  treeRef.value?.filter(val);
});

function filterNode(value: string, data: DeptTreeNode): boolean {
  if (!value) return true;
  return data.name.indexOf(value) !== -1;
}

async function getDeptTree() {
  try {
    const res: any = await api.GetDept();
    if (res?.code === 2000 && Array.isArray(res.data)) {
      const result = XEUtils.toArrayTree(res.data, {
        parentKey: 'parent',
        children: 'children',
        strict: true,
      });
      deptTreeData.value = result;
    }
  } catch (e) {
    console.error('Failed to fetch dept tree', e);
  }
}

function onTreeNodeClick(data: DeptTreeNode) {
  if (data && data.id) {
    currentDeptId.value = data.id;
    currentDeptName.value = data.name;
  } else {
    currentDeptId.value = null;
    currentDeptName.value = '';
  }
  page.value = 1;
  getList();
}

// ============================================================
// Table State
// ============================================================
const loading = ref(false);
const tableData = ref<UserRecord[]>([]);
const page = ref(1);
const limit = ref(20);
const total = ref(0);

const searchForm = reactive({
  username: '',
  name: '',
  mobile: '',
});

async function getList() {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: page.value,
      limit: limit.value,
    };
    if (searchForm.username) params.username = searchForm.username;
    if (searchForm.name) params.name = searchForm.name;
    if (searchForm.mobile) params.mobile = searchForm.mobile;
    if (currentDeptId.value) params.dept = currentDeptId.value;

    const res: any = await api.GetList(params);
    if (res?.code === 2000) {
      const data: UserRecord[] = res.data || [];
      tableData.value = data;
      total.value = res.total || data.length;
      computeStats(data);
      // Set deptUserCount = count of visible rows when dept filter is active
      if (currentDeptId.value) {
        stats.deptUserCount = data.length;
      }
    } else {
      tableData.value = [];
      total.value = 0;
    }
  } catch (e) {
    console.error('Failed to fetch user list', e);
    tableData.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

function handleSearch() {
  page.value = 1;
  getList();
}

function resetSearch() {
  searchForm.username = '';
  searchForm.name = '';
  searchForm.mobile = '';
  page.value = 1;
  getList();
}

// ============================================================
// Role display helper
// ============================================================
function resolveRoles(row: UserRecord): any[] {
  // Try role_info (array of objects) first, then role (array of ids)
  if (row.role_info && row.role_info.length > 0) {
    return row.role_info;
  }
  if (row.role && row.role.length > 0) {
    // Map ids to names from roleOptions
    return row.role.map((id: number) => {
      const found = roleOptions.value.find((r) => r.id === id);
      return found || { id, name: String(id) };
    });
  }
  return [];
}

// ============================================================
// is_active switch toggle
// ============================================================
async function handleActiveChange(row: UserRecord, val: boolean) {
  const original = row.is_active;
  row.is_active = val;
  row._switchLoading = true;
  try {
    const res: any = await api.UpdateObj({
      id: row.id,
      is_active: val,
    });
    if (res?.code === 2000) {
      successMessage(res.msg || '操作成功');
    } else {
      row.is_active = original;
    }
  } catch (e) {
    row.is_active = original;
  } finally {
    row._switchLoading = false;
  }
}

// ============================================================
// Add / Edit Dialog
// ============================================================
const dialogVisible = ref(false);
const dialogType = ref<'add' | 'edit'>('add');
const submitLoading = ref(false);
const formRef = ref<FormInstance>();

const formData = reactive({
  id: 0,
  username: '',
  password: '',
  name: '',
  dept: null as number | null,
  role: [] as number[],
  mobile: '',
  email: '',
  gender: 1,
  is_active: true,
  user_type: 0,
});

const deptSelectProps = {
  children: 'children',
  label: 'name',
  value: 'id',
};

const formRules: FormRules = {
  username: [
    { required: true, message: '账号为必填项', trigger: 'blur' },
    { min: 2, max: 150, message: '账号长度在 2 到 150 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '密码为必填项', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于 6 位', trigger: 'blur' },
  ],
  name: [
    { required: true, message: '姓名为必填项', trigger: 'blur' },
  ],
  dept: [
    { required: true, message: '部门为必选项', trigger: 'change' },
  ],
  role: [
    { required: true, message: '角色为必选项', trigger: 'change' },
  ],
  mobile: [
    {
      pattern: /^1[3-9]\d{9}$/,
      message: '请输入正确的手机号码',
      trigger: 'blur',
    },
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: ['blur', 'change'] },
  ],
};

function openAddDialog() {
  dialogType.value = 'add';
  formData.id = 0;
  formData.username = '';
  formData.password = defaultPassword.value;
  formData.name = '';
  formData.dept = null;
  formData.role = [];
  formData.mobile = '';
  formData.email = '';
  formData.gender = 1;
  formData.is_active = true;
  formData.user_type = 0;
  dialogVisible.value = true;
}

function openEditDialog(row: UserRecord) {
  dialogType.value = 'edit';
  formData.id = row.id;
  formData.username = row.username;
  formData.password = ''; // Not shown in edit
  formData.name = row.name;
  formData.dept = row.dept?.id ?? null;
  formData.role = row.role || [];
  formData.mobile = row.mobile || '';
  formData.email = row.email || '';
  formData.gender = row.gender ?? 1;
  formData.is_active = row.is_active ?? true;
  formData.user_type = row.user_type ?? 0;
  dialogVisible.value = true;
}

function resetForm() {
  formRef.value?.resetFields();
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  submitLoading.value = true;
  try {
    const payload = { ...formData };

    // MD5 hash password for add
    if (dialogType.value === 'add' && payload.password) {
      payload.password = Md5.hashStr(payload.password);
    }

    // Clean up: id is not sent in payload body for add
    if (dialogType.value === 'add') {
      delete payload.id;
    }

    let res: any;
    if (dialogType.value === 'add') {
      res = await api.AddObj(payload);
    } else {
      res = await api.UpdateObj(payload);
    }

    if (res?.code === 2000) {
      successMessage(res.msg || (dialogType.value === 'add' ? '新增成功' : '更新成功'));
      dialogVisible.value = false;
      getList();
    }
  } catch (e) {
    console.error('Submit failed', e);
  } finally {
    submitLoading.value = false;
  }
}

// ============================================================
// Delete
// ============================================================
async function handleDelete(row: UserRecord) {
  try {
    await ElMessageBox.confirm('是否删除该用户？', '温馨提示', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    });
    const res: any = await api.DelObj(row.id);
    if (res?.code === 2000) {
      successNotification(res.msg || '删除成功');
      getList();
    }
  } catch (e) {
    // cancelled or error
  }
}

// ============================================================
// Export
// ============================================================
async function handleExport() {
  try {
    const params: Record<string, any> = {};
    if (searchForm.username) params.username = searchForm.username;
    if (searchForm.name) params.name = searchForm.name;
    if (searchForm.mobile) params.mobile = searchForm.mobile;
    if (currentDeptId.value) params.dept = currentDeptId.value;

    await api.exportData(params);
  } catch (e) {
    console.error('Export failed', e);
  }
}

// ============================================================
// Reset Password Dialog
// ============================================================
const resetPwdVisible = ref(false);
const resetPwdLoading = ref(false);
const resetPwdFormRef = ref<FormInstance>();
const resetPwdTargetId = ref<number>(0);

const resetPwdForm = reactive({
  newPassword: '',
  newPassword2: '',
});

const resetPwdRules: FormRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于 6 位', trigger: 'blur' },
  ],
  newPassword2: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: Function) => {
        if (value !== resetPwdForm.newPassword) {
          callback(new Error('两次输入密码不一致'));
        } else {
          callback();
        }
      },
      trigger: 'blur',
    },
  ],
};

function openResetPwdDialog(row: UserRecord) {
  resetPwdTargetId.value = row.id;
  resetPwdForm.newPassword = '';
  resetPwdForm.newPassword2 = '';
  resetPwdVisible.value = true;
}

function resetResetPwdForm() {
  resetPwdFormRef.value?.resetFields();
  resetPwdTargetId.value = 0;
}

async function handleResetPwdSubmit() {
  const valid = await resetPwdFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  resetPwdLoading.value = true;
  try {
    const res: any = await api.resetPwd(resetPwdTargetId.value, {
      new_password: Md5.hashStr(resetPwdForm.newPassword),
      new_password2: Md5.hashStr(resetPwdForm.newPassword2),
    });
    if (res?.code === 2000) {
      successNotification(res.msg || '密码重置成功');
      resetPwdVisible.value = false;
    }
  } catch (e) {
    console.error('Reset password failed', e);
  } finally {
    resetPwdLoading.value = false;
  }
}

// ============================================================
// Lifecycle
// ============================================================
onMounted(async () => {
  await Promise.all([getDeptTree(), fetchRoleOptions(), fetchDeptSelectData()]);
  getList();
});
</script>

<style lang="scss" scoped>
.user-page {
  height: 100%;
  overflow-y: auto;
  padding: 0 4px;
  box-sizing: border-box;
}

// ============================================================
// Stats Cards
// ============================================================
.stats-row {
  margin-bottom: 10px;
}

.stats-card {
  border-radius: 8px;
  text-align: center;
  padding: 6px 0;

  .stats-value {
    font-size: 30px;
    font-weight: 700;
    line-height: 1.2;
  }

  .stats-label {
    font-size: 13px;
    color: #909399;
    margin-top: 4px;
  }
}

.stats-total {
  --stats-color: #409eff;
  border-left: 4px solid #409eff;
  .stats-value { color: #409eff; }
}

.stats-active {
  --stats-color: #67c23a;
  border-left: 4px solid #67c23a;
  .stats-value { color: #67c23a; }
}

.stats-inactive {
  --stats-color: #f56c6c;
  border-left: 4px solid #f56c6c;
  .stats-value { color: #f56c6c; }
}

.stats-dept {
  --stats-color: #e6a23c;
  border-left: 4px solid #e6a23c;
  .stats-value { color: #e6a23c; }
}

// ============================================================
// Main Content Row
// ============================================================
.main-row {
  height: calc(100% - 90px);

  .left-col, .right-col {
    height: 100%;
  }

  .el-card {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .el-card__body {
    flex: 1;
    overflow: auto;
  }
}

// ============================================================
// Tree Card (Left Column)
// ============================================================
.tree-card {
  .tree-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .tree-header-title {
      font-weight: 700;
      font-size: 15px;
    }
  }

  .tree-filter {
    margin-bottom: 10px;
  }

  .tree-node-label {
    display: flex;
    align-items: center;
    font-size: 13px;
  }
}

// ============================================================
// Table Card (Right Column)
// ============================================================
.table-card {
  .table-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    margin-bottom: 12px;

    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .toolbar-right {
      .search-form {
        :deep(.el-form-item) {
          margin-bottom: 0;
          margin-right: 8px;
        }
      }
    }
  }

  .pagination-wrap {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
}

// ============================================================
// Role Tags in Table
// ============================================================
.role-tag {
  margin-right: 4px;
  margin-bottom: 2px;
}

// ============================================================
// Responsive Adjustments
// ============================================================
@media (max-width: 1200px) {
  .main-row {
    height: auto;
  }

  .left-col {
    :deep(.el-col) {
      width: 100%;
    }
  }
}
</style>
