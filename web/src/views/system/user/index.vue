<template>
  <div class="sys-page user-page">
    <!-- ===== Stats Cards ===== -->
    <div class="user-stats sys-fade-in-up">
      <div v-for="s in stats" :key="s.label" class="user-stat-card">
        <div class="user-stat-icon" :style="{ background: s.bg }">
          <el-icon :size="20"><component :is="s.icon" /></el-icon>
        </div>
        <div class="user-stat-body">
          <div class="user-stat-val">{{ s.value }}</div>
          <div class="user-stat-lbl">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <!-- ===== Main Content ===== -->
    <el-row class="user-main-row" :gutter="14">
      <!-- Left: Department Tree -->
      <el-col :xs="24" :sm="5" class="user-col">
        <div class="sys-card user-tree-card sys-fade-in-up" style="animation-delay:0.06s">
          <div class="user-section-header">
            <span class="user-header-icon"><el-icon :size="15"><OfficeBuilding /></el-icon></span>
            <span>部门列表</span>
            <el-tooltip content="点击部门节点筛选用户" placement="right">
              <el-icon style="margin-left:auto;cursor:pointer;color:#909399" :size="14"><QuestionFilled /></el-icon>
            </el-tooltip>
          </div>
          <div class="user-tree-body">
            <el-input v-model="filterText" placeholder="搜索部门..." clearable size="small" :prefix-icon="Search" class="user-tree-filter" />
            <div class="user-tree-scroll">
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
                  <span class="user-tree-node">
                    <SvgIcon name="iconfont icon-shouye" />&nbsp;{{ data.name }}
                  </span>
                </template>
              </el-tree>
            </div>
          </div>
        </div>
      </el-col>

      <!-- Right: User Table -->
      <el-col :xs="24" :sm="19" class="user-col">
        <div class="sys-card user-table-card sys-fade-in-up" style="animation-delay:0.1s">
          <div class="user-section-header user-section-header-table">
            <span class="user-header-icon user-header-icon-accent"><el-icon :size="15"><User /></el-icon></span>
            <span>用户管理</span>
            <span v-if="currentDeptName" class="user-header-dept">{{ currentDeptName }}</span>
            <span class="user-header-badge">User Management</span>
          </div>

          <!-- Toolbar -->
          <div class="user-toolbar">
            <div class="user-toolbar-left">
              <el-button v-if="auth('user:Create')" type="primary" size="small" :icon="Plus" @click="openAddDialog">新增</el-button>
              <el-button v-if="auth('user:Export')" size="small" @click="handleExport">导出</el-button>
              <importExcel v-if="auth('user:Import')" api="api/system/user/" />
            </div>
            <div class="user-toolbar-right">
              <el-input v-model="searchForm.username" placeholder="账号" clearable size="small" style="width:130px" @keyup.enter="handleSearch" />
              <el-input v-model="searchForm.name" placeholder="姓名" clearable size="small" style="width:120px" @keyup.enter="handleSearch" />
              <el-input v-model="searchForm.mobile" placeholder="手机号" clearable size="small" style="width:130px" @keyup.enter="handleSearch" />
              <el-button type="primary" size="small" @click="handleSearch">搜索</el-button>
              <el-button size="small" @click="resetSearch">重置</el-button>
            </div>
          </div>

          <!-- Table -->
          <el-table :data="tableData" v-loading="loading" stripe size="small" style="width:100%" row-key="id" class="user-table">
            <el-table-column type="index" label="#" width="50" align="center" />
            <el-table-column prop="username" label="账号" min-width="110" show-overflow-tooltip />
            <el-table-column prop="name" label="姓名" min-width="90" show-overflow-tooltip />
            <el-table-column label="部门" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.dept_name || row.dept?.name || '-' }}</template>
            </el-table-column>
            <el-table-column label="角色" min-width="140">
              <template #default="{ row }">
                <el-tag v-for="r in resolveRoles(row)" :key="r.id || r" size="small" class="user-role-tag">{{ r.name || r }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="mobile" label="手机号" width="120" />
            <el-table-column prop="email" label="邮箱" min-width="160" show-overflow-tooltip />
            <el-table-column label="性别" width="60" align="center">
              <template #default="{ row }">{{ getDictLabel('gender', row.gender) }}</template>
            </el-table-column>
            <el-table-column label="类型" width="80" align="center">
              <template #default="{ row }">{{ getDictLabel('user_type', row.user_type) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="70" align="center">
              <template #default="{ row }">
                <el-switch :model-value="Boolean(row.is_active)" size="small" @change="(val) => handleActiveChange(row, val)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="250" fixed="right" align="center">
              <template #default="{ row }">
                <el-button v-if="auth('user:Update')" text type="primary" size="small" style="padding:0 4px" @click="openEditDialog(row)">编辑</el-button>
                <el-button v-if="auth('user:Delete')" text type="danger" size="small" style="padding:0 4px" @click="handleDelete(row)">删除</el-button>
                <el-button v-if="auth('user:ResetPassword')" text type="warning" size="small" style="padding:0 4px" @click="openResetPwdDialog(row)">重置密码</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- Pagination -->
          <div class="user-pagination">
            <el-pagination v-model:current-page="page" v-model:page-size="limit" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next, jumper" background small @size-change="getList" @current-change="getList" />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ===== Add/Edit Dialog ===== -->
    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增用户' : '编辑用户'" width="640px" :close-on-click-modal="false" :destroy-on-close="true" @close="resetForm" class="opsflow-dialog">
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="90px" size="small">
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="账号" prop="username"><el-input v-model="formData.username" placeholder="请输入登录账号" maxlength="150" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="姓名" prop="name"><el-input v-model="formData.name" placeholder="请输入真实姓名" maxlength="50" /></el-form-item></el-col>
          <el-col :span="12" v-if="dialogType==='add'"><el-form-item label="密码" prop="password"><el-input v-model="formData.password" type="password" show-password placeholder="默认: 123456" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="部门" prop="dept"><el-tree-select v-model="formData.dept" :data="deptSelectData" :props="deptSelectProps" placeholder="请选择部门" filterable check-strictly clearable style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="角色" prop="role"><el-select v-model="formData.role" multiple filterable placeholder="请选择角色" style="width:100%"><el-option v-for="item in roleOptions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="手机号" prop="mobile"><el-input v-model="formData.mobile" placeholder="11 位手机号" maxlength="11" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="邮箱" prop="email"><el-input v-model="formData.email" placeholder="电子邮箱" maxlength="100" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="性别"><el-select v-model="formData.gender" placeholder="请选择" style="width:100%"><el-option v-for="item in genderDict" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="启用"><el-switch v-model="formData.is_active" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button size="small" @click="dialogVisible = false">取消</el-button>
        <el-button size="small" type="primary" :loading="submitLoading" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- ===== Reset Password Dialog ===== -->
    <el-dialog v-model="resetPwdVisible" title="重设密码" width="420px" :close-on-click-modal="false" :destroy-on-close="true" @close="resetResetPwdForm" class="opsflow-dialog">
      <el-form ref="resetPwdFormRef" :model="resetPwdForm" :rules="resetPwdRules" label-width="90px" size="small">
        <el-form-item label="新密码" prop="newPassword"><el-input v-model="resetPwdForm.newPassword" type="password" show-password placeholder="8-30 位，含字母和数字" /></el-form-item>
        <el-form-item label="确认密码" prop="newPassword2"><el-input v-model="resetPwdForm.newPassword2" type="password" show-password placeholder="再次输入新密码" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="resetPwdVisible = false">取消</el-button>
        <el-button size="small" type="primary" :loading="resetPwdLoading" @click="handleResetPwdSubmit">保存</el-button>
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
import { Plus, Search, User, OfficeBuilding, Male, Female, QuestionFilled } from '@element-plus/icons-vue';
import SvgIcon from '/@/components/SvgIcon/index.vue';
import importExcel from '/@/components/importExcel/index.vue';
import { auth } from '/@/utils/authFunction';
import { dictionary } from '/@/utils/dictionary';
import { successMessage, successNotification } from '/@/utils/message';
import { request } from '/@/utils/service';
import { SystemConfigStore } from '/@/stores/systemConfig';
import * as api from './api';

/* ===================== Types ===================== */
interface DeptTreeNode { id: number; name: string; parent?: number; status?: boolean; children?: DeptTreeNode[]; }
interface UserRecord { id: number; username: string; name: string; dept?: { id: number; name: string }; dept_name?: string; role?: number[]; role_info?: { id: number; name: string }[]; mobile?: string; email?: string; gender?: number; user_type?: number; is_active?: boolean; avatar?: string; _switchLoading?: boolean; [key: string]: any; }
interface RoleItem { id: number; name: string; [key: string]: any; }

/* ===================== Provide ===================== */
provide('refreshView', () => getList());

/* ===================== Store ===================== */
const systemConfigStore = SystemConfigStore();
const defaultPassword = computed(() => systemConfigStore.systemConfig?.['base.default_password'] || '123456');

/* ===================== Stats ===================== */
const statsArr = ref([
  { label: '用户总数', value: 0, icon: User, bg: 'linear-gradient(135deg,#409eff,#337ecc)' },
  { label: '活跃用户', value: 0, icon: Male, bg: 'linear-gradient(135deg,#67c23a,#409eff)' },
  { label: '锁定用户', value: 0, icon: Female, bg: 'linear-gradient(135deg,#f56c6c,#e6a23c)' },
  { label: '当前部门', value: '--', icon: OfficeBuilding, bg: 'linear-gradient(135deg,#909399,#606266)' },
]);
const stats = computed(() => statsArr.value);

function updateStats(data: UserRecord[]) {
  let active = 0, inactive = 0;
  data.forEach(u => { if (u.is_active) active++; else inactive++; });
  statsArr.value[0].value = total.value;
  statsArr.value[1].value = active;
  statsArr.value[2].value = inactive;
  statsArr.value[3].value = currentDeptId.value ? data.length : total.value;
}

/* ===================== Dict ===================== */
const genderDict = computed(() => (dictionary('gender') as any[]) || []);
function getDictLabel(dictName: string, value: number | string | undefined): string {
  if (value === undefined || value === null) return '-';
  const items = dictionary(dictName) as any[];
  const found = items?.find((d: any) => d.value === value);
  return found ? found.label : String(value);
}

/* ===================== Roles & Depts ===================== */
const roleOptions = ref<RoleItem[]>([]);
const deptSelectData = ref<any[]>([]);
async function fetchRoleOptions() {
  try { const res: any = await request({ url: '/api/system/role/', method: 'get' }); if (res?.code === 2000) roleOptions.value = res.data || []; } catch {}
}
async function fetchDeptSelectData() {
  try { const res: any = await request({ url: '/api/system/dept/all_dept/', method: 'get' }); if (res?.code === 2000 && Array.isArray(res.data)) deptSelectData.value = res.data; } catch {}
}

/* ===================== Dept Tree ===================== */
const filterText = ref('');
const treeRef = ref<any>(null);
const deptTreeData = ref<DeptTreeNode[]>([]);
const currentDeptId = ref<number | null>(null);
const currentDeptName = ref('');
const treeProps = { children: 'children', label: 'name' };
watch(filterText, v => treeRef.value?.filter(v));
function filterNode(value: string, data: DeptTreeNode) { return !value || data.name.indexOf(value) !== -1; }
async function getDeptTree() {
  try { const res: any = await api.GetDept(); if (res?.code === 2000 && Array.isArray(res.data)) deptTreeData.value = XEUtils.toArrayTree(res.data, { parentKey: 'parent', children: 'children', strict: true }); } catch {}
}
function onTreeNodeClick(data: DeptTreeNode) {
  currentDeptId.value = data?.id || null;
  currentDeptName.value = data?.name || '';
  page.value = 1;
  getList();
}

/* ===================== Table ===================== */
const loading = ref(false);
const tableData = ref<UserRecord[]>([]);
const page = ref(1);
const limit = ref(20);
const total = ref(0);
const searchForm = reactive({ username: '', name: '', mobile: '' });

async function getList() {
  loading.value = true;
  try {
    const params: Record<string, any> = { page: page.value, limit: limit.value };
    if (searchForm.username) params.username = searchForm.username;
    if (searchForm.name) params.name = searchForm.name;
    if (searchForm.mobile) params.mobile = searchForm.mobile;
    if (currentDeptId.value) params.dept = currentDeptId.value;
    const res: any = await api.GetList(params);
    if (res?.code === 2000) {
      tableData.value = res.data || [];
      total.value = res.total || tableData.value.length;
      updateStats(tableData.value);
    } else { tableData.value = []; total.value = 0; }
  } catch { tableData.value = []; total.value = 0; }
  finally { loading.value = false; }
}
function handleSearch() { page.value = 1; getList(); }
function resetSearch() { Object.assign(searchForm, { username: '', name: '', mobile: '' }); page.value = 1; getList(); }

/* ===================== Helpers ===================== */
function resolveRoles(row: UserRecord): any[] {
  if (row.role_info?.length) return row.role_info;
  if (row.role?.length) return row.role.map((id: number) => roleOptions.value.find(r => r.id === id) || { id, name: String(id) });
  return [];
}

/* ===================== Switch ===================== */
async function handleActiveChange(row: UserRecord, val: boolean) {
  const orig = row.is_active;
  row.is_active = val; row._switchLoading = true;
  try { const res: any = await api.UpdateObj({ id: row.id, is_active: val }); if (res?.code !== 2000) row.is_active = orig; }
  catch { row.is_active = orig; }
  finally { row._switchLoading = false; }
}

/* ===================== Dialog ===================== */
const dialogVisible = ref(false);
const dialogType = ref<'add' | 'edit'>('add');
const submitLoading = ref(false);
const formRef = ref<FormInstance>();
const formData = reactive({ id: 0, username: '', password: '', name: '', dept: null as number | null, role: [] as number[], mobile: '', email: '', gender: 1, is_active: true, user_type: 0 });
const deptSelectProps = { children: 'children', label: 'name', value: 'id' };
const formRules: FormRules = {
  username: [{ required: true, message: '必填项', trigger: 'blur' }, { min: 2, max: 150, message: '长度 2-150', trigger: 'blur' }],
  password: [{ required: true, message: '必填项', trigger: 'blur' }, { min: 6, message: '至少 6 位', trigger: 'blur' }],
  name: [{ required: true, message: '必填项', trigger: 'blur' }],
  dept: [{ required: true, message: '必选项', trigger: 'change' }],
  role: [{ required: true, message: '必选项', trigger: 'change' }],
  mobile: [{ pattern: /^1[3-9]\d{9}$/, message: '格式不正确', trigger: 'blur' }],
  email: [{ type: 'email' as const, message: '格式不正确', trigger: ['blur', 'change'] }],
};

function openAddDialog() {
  dialogType.value = 'add';
  Object.assign(formData, { id: 0, username: '', password: defaultPassword.value, name: '', dept: null, role: [], mobile: '', email: '', gender: 1, is_active: true, user_type: 0 });
  dialogVisible.value = true;
}
function openEditDialog(row: UserRecord) {
  dialogType.value = 'edit';
  Object.assign(formData, { id: row.id, username: row.username, password: '', name: row.name, dept: row.dept?.id ?? null, role: row.role || [], mobile: row.mobile || '', email: row.email || '', gender: row.gender ?? 1, is_active: row.is_active ?? true, user_type: row.user_type ?? 0 });
  dialogVisible.value = true;
}
function resetForm() { formRef.value?.resetFields(); }

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitLoading.value = true;
  try {
    const payload = { ...formData };
    if (dialogType.value === 'add' && payload.password) payload.password = Md5.hashStr(payload.password);
    if (dialogType.value === 'add') delete payload.id;
    const res = dialogType.value === 'add' ? await api.AddObj(payload) : await api.UpdateObj(payload);
    if (res?.code === 2000) { successMessage(res.msg || '操作成功'); dialogVisible.value = false; getList(); }
  } finally { submitLoading.value = false; }
}

/* ===================== Delete ===================== */
async function handleDelete(row: UserRecord) {
  try {
    await ElMessageBox.confirm('确认删除该用户？', '确认', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' });
    const res: any = await api.DelObj(row.id);
    if (res?.code === 2000) { successNotification(res.msg || '删除成功'); getList(); }
  } catch {}
}

/* ===================== Export ===================== */
async function handleExport() {
  try {
    const params: Record<string, any> = {};
    if (searchForm.username) params.username = searchForm.username;
    if (searchForm.name) params.name = searchForm.name;
    if (searchForm.mobile) params.mobile = searchForm.mobile;
    if (currentDeptId.value) params.dept = currentDeptId.value;
    await api.exportData(params);
  } catch {}
}

/* ===================== Reset Pwd ===================== */
const resetPwdVisible = ref(false);
const resetPwdLoading = ref(false);
const resetPwdFormRef = ref<FormInstance>();
const resetPwdTargetId = ref(0);
const resetPwdForm = reactive({ newPassword: '', newPassword2: '' });
const resetPwdRules: FormRules = {
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { pattern: /(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}/, message: '需包含字母和数字', trigger: 'blur' }],
  newPassword2: [{ required: true, message: '请再次输入', trigger: 'blur' }, { validator: (_r: any, v: string, cb: Function) => v !== resetPwdForm.newPassword ? cb(new Error('两次输入不一致')) : cb(), trigger: 'blur' }],
};
function openResetPwdDialog(row: UserRecord) { resetPwdTargetId.value = row.id; resetPwdForm.newPassword = ''; resetPwdForm.newPassword2 = ''; resetPwdVisible.value = true; }
function resetResetPwdForm() { resetPwdFormRef.value?.resetFields(); resetPwdTargetId.value = 0; }
async function handleResetPwdSubmit() {
  const valid = await resetPwdFormRef.value?.validate().catch(() => false);
  if (!valid) return;
  resetPwdLoading.value = true;
  try {
    const res: any = await api.resetPwd(resetPwdTargetId.value, { new_password: Md5.hashStr(resetPwdForm.newPassword), new_password2: Md5.hashStr(resetPwdForm.newPassword2) });
    if (res?.code === 2000) { successNotification(res.msg || '重置成功'); resetPwdVisible.value = false; }
  } finally { resetPwdLoading.value = false; }
}

/* ===================== Init ===================== */
onMounted(async () => { await Promise.all([getDeptTree(), fetchRoleOptions(), fetchDeptSelectData()]); getList(); });
</script>

<style scoped lang="scss">
@use '../../../styles/opsflow-global' as *;

.user-page { width: 100%; height: 100%; }
.sys-page { height: 100%; background: $of-bg-page; display: flex; flex-direction: column; overflow: hidden; }

// ===== Stats =====
.user-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 16px; padding: 12px 12px 0; }
.user-stat-card { display: flex; align-items: center; gap: 14px; background: #fff; border-radius: $of-radius-card; padding: 16px 18px; box-shadow: $of-shadow-card; transition: transform .2s, box-shadow .2s; cursor: default; &:hover { transform: translateY(-2px); box-shadow: $of-shadow-hover; } }
.user-stat-icon { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; color: #fff; }
.user-stat-body { flex: 1; min-width: 0; }
.user-stat-val { font-size: 22px; font-weight: 700; color: $of-text-primary; line-height: 1.2; }
.user-stat-lbl { font-size: 13px; color: $of-text-secondary; margin-top: 2px; }

// ===== Layout =====
.user-main-row { height: calc(100vh - 180px); overflow: hidden; margin: 0 12px !important; .el-col { height: 100%; } }
.sys-card { background: #fff; border: 1px solid $of-border-card; border-radius: $of-radius-card; height: 100%; display: flex; flex-direction: column; overflow: hidden; box-shadow: $of-shadow-card; transition: box-shadow $of-transition-default; }

// ===== Section Header =====
.user-section-header { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: $of-gradient-hero; border-bottom: 1px solid $of-border-light; font-size: 14px; font-weight: 600; color: $of-text-primary; flex-shrink: 0; }
.user-section-header-table { background: linear-gradient(135deg, #f0f5ff 0%, #fafbfc 100%); }
.user-header-icon { @include of-icon-circle(30px, $of-gradient-blue); }
.user-header-icon-accent { background: $of-gradient-accent; }
.user-header-badge { margin-left: auto; font-size: 11px; font-weight: 400; color: $of-text-muted; }
.user-header-dept { font-size: 12px; font-weight: 400; color: $of-color-primary; background: $of-bg-light-blue; padding: 2px 10px; border-radius: 10px; }

// ===== Tree =====
.user-tree-body { flex: 1; display: flex; flex-direction: column; padding: 12px; overflow: hidden; }
.user-tree-filter { margin-bottom: 8px; }
.user-tree-scroll { flex: 1; overflow-y: auto; }
.user-tree-node { font-size: 13px; display: inline-flex; align-items: center; }

// ===== Table Card =====
.user-table-card {
  .el-card__body { flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 0 !important; }
}
.user-table { flex: 1; overflow: auto; }
.user-table :deep(th.el-table__cell) { background: $of-bg-header; color: $of-text-primary; font-weight: 600; font-size: 12px; }

// ===== Toolbar =====
.user-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; flex-shrink: 0; border-bottom: 1px solid $of-border-light; flex-wrap: wrap; gap: 8px; }
.user-toolbar-left, .user-toolbar-right { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }

// ===== Tags =====
.user-role-tag { margin-right: 2px; margin-bottom: 2px; }

// ===== Pagination =====
.user-pagination { display: flex; justify-content: flex-end; padding: 10px 16px; flex-shrink: 0; border-top: 1px solid $of-border-light; }
</style>
