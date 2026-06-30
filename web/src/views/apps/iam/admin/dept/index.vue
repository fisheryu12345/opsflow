<template>
  <div class="sys-page dept-page">
    <!-- ===== Stats Row ===== -->
    <div class="dept-stats sys-fade-in-up">
      <div v-for="s in stats" :key="s.label" class="dept-stat-card">
        <div class="dept-stat-icon" :style="{ background: s.bg }">
          <el-icon :size="20"><component :is="s.icon" /></el-icon>
        </div>
        <div class="dept-stat-body">
          <div class="dept-stat-val">{{ s.value }}</div>
          <div class="dept-stat-lbl">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <el-row :gutter="14" class="dept-main-row">
      <!-- ===== Left: Tree ===== -->
      <el-col :xs="24" :sm="6">
        <div class="sys-card dept-tree-wrap sys-fade-in-up" style="animation-delay:0.06s">
          <DeptTreeCom
            ref="deptTreeRef"
            :treeData="deptTreeData"
            @treeClick="handleTreeClick"
            @updateDept="handleUpdateMenu"
            @deleteDept="handleDeleteMenu"
          />
        </div>
      </el-col>

      <!-- ===== Right: Content ===== -->
      <el-col :xs="24" :sm="18">
        <div class="sys-card dept-content sys-fade-in-up" style="animation-delay:0.1s">

          <!-- Empty state -->
          <div v-if="!currentDeptId" class="dept-empty">
            <el-empty :image-size="80" :description="$t('message.menuPage.deptSelectOnLeft')">
              <el-tag type="info" effect="plain" round>{{ $t('message.menuPage.deptClickNode') }}</el-tag>
            </el-empty>
          </div>

          <!-- Dept selected -->
          <template v-else>
            <!-- Breadcrumb-style dept header -->
            <div class="dept-bread">
              <el-icon color="#409eff" :size="18"><OfficeBuilding /></el-icon>
              <span class="dept-bread-name">{{ deptInfo.dept_name || currentDeptName }}</span>
              <el-tag size="small" effect="plain" round type="info" class="dept-bread-tag">
                {{ deptInfo.dept_user ?? 0 }} {{ $t('message.menuPage.deptMembers') }}
              </el-tag>
              <span class="dept-bread-switch">
                <span class="dept-bread-switch-label">{{ $t('message.menuPage.deptIncludeChildren') }}</span>
                <el-switch
                  v-model="isShowChildFlag"
                  size="small"
                  @change="handleSwitchChange"
                />
              </span>
            </div>

            <!-- Info cards + Charts -->
            <div class="dept-dashboard">
              <div class="dept-dash-info">
                <div class="dept-info-row">
                  <span class="dept-info-label">{{ $t('message.menuPage.deptOwner') }}</span>
                  <span class="dept-info-val">{{ deptInfo.owner || $t('message.menuPage.deptNoOwner') }}</span>
                </div>
                <div class="dept-info-row">
                  <span class="dept-info-label">{{ $t('message.menuPage.deptDesc') }}</span>
                  <span class="dept-info-val dept-info-desc">{{ deptInfo.description || $t('message.menuPage.deptNoDesc') }}</span>
                </div>
              </div>
              <div class="dept-dash-charts">
                <div ref="deptCountBarRef" class="dept-chart dept-chart-bar" />
                <div ref="deptSexPieRef" class="dept-chart dept-chart-pie" />
              </div>
            </div>

            <!-- Toolbar -->
            <div class="dept-toolbar">
              <div class="dept-toolbar-left">
                <el-button type="primary" size="small" :icon="Plus" @click="handleAddUser">
                  {{ $t('message.menuPage.deptAddUser') }}
                </el-button>
                <el-button size="small" :icon="Refresh" @click="handleRefreshAll">{{ $t('message.menuPage.deptRefresh') }}</el-button>
              </div>
              <div class="dept-toolbar-right">
                <el-input
                  v-model="searchKeyword"
                  :placeholder="$t('message.menuPage.deptSearchUser')"
                  clearable
                  size="small"
                  style="width:210px"
                  :prefix-icon="Search"
                  @clear="handleSearch"
                  @keyup.enter="handleSearch"
                />
              </div>
            </div>

            <!-- User Table -->
            <el-table
              :data="userList"
              v-loading="userLoading"
              stripe
              size="small"
              style="width:100%"
              row-key="id"
              :empty-text="$t('message.menuPage.deptNoUsers')"
            >
              <el-table-column type="index" label="#" width="50" align="center" />
              <el-table-column prop="username" :label="$t('message.menuPage.deptColAccount')" min-width="100" show-overflow-tooltip />
              <el-table-column prop="name" :label="$t('message.menuPage.deptColName')" min-width="90" show-overflow-tooltip />
              <el-table-column :label="$t('message.menuPage.deptColRole')" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ getRoleNames(row.role) }}</template>
              </el-table-column>
              <el-table-column prop="mobile" :label="$t('message.menuPage.deptColPhone')" min-width="110" />
              <el-table-column prop="email" :label="$t('message.menuPage.deptColEmail')" min-width="140" show-overflow-tooltip />
              <el-table-column :label="$t('message.menuPage.deptColGender')" width="60" align="center">
                <template #default="{ row }">{{ displayGender(row.gender) }}</template>
              </el-table-column>
              <el-table-column :label="$t('message.menuPage.deptColStatus')" width="70" align="center">
                <template #default="{ row }">
                  <el-switch
                    v-model="row.is_active"
                    :active-value="true"
                    :inactive-value="false"
                    size="small"
                    @change="() => handleToggleActive(row)"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="$t('message.menuPage.deptColActions')" width="235" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button text size="small" style="padding:0 4px" @click="handleEditUser(row)">{{ $t('message.menuPage.deptEditUser') }}</el-button>
                  <el-button text type="danger" size="small" style="padding:0 4px" @click="handleDeleteUser(row)">{{ $t('message.menuPage.deptDeleteUser') }}</el-button>
                  <el-button text type="warning" size="small" style="padding:0 4px" @click="handleResetPwdOpen(row)">{{ $t('message.menuPage.deptResetPwd') }}</el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- Pagination -->
            <div class="dept-pagination">
              <el-pagination
                v-model:currentPage="pageParams.current"
                v-model:pageSize="pageParams.pageSize"
                :total="pageParams.total"
                :page-sizes="[10,20,50,100]"
                layout="total, sizes, prev, pager, next, jumper"
                background
                size="small"
                @update:pageSize="handlePageChange"
                @update:currentPage="handlePageChange"
              />
            </div>
          </template>
        </div>
      </el-col>
    </el-row>

    <!-- ===== Dept Drawer ===== -->
    <el-drawer
      v-model="drawerVisible"
      :title="$t('message.menuPage.deptEditDept')"
      direction="rtl"
      size="480px"
      :close-on-click-modal="false"
      :before-close="handleDrawerClose"
      class="opsflow-drawer"
    >
      <DeptFormCom
        v-if="drawerVisible"
        :initFormData="drawerFormData"
        :treeData="deptTreeData"
        :cacheData="deptTreeCacheData"
        @drawerClose="handleDrawerClose"
      />
    </el-drawer>

    <!-- ===== User Dialog ===== -->
    <el-dialog
      v-model="userDialogVisible"
      :title="isEditUser ? $t('message.menuPage.deptEditUserTitle') : $t('message.menuPage.deptAddUserTitle')"
      width="580px"
      :close-on-click-modal="false"
      @closed="handleUserDialogClose"
      class="opsflow-dialog"
    >
      <el-form ref="userFormRef" :model="userForm" :rules="userFormRules" label-width="90px" size="small">
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item :label="$t('message.menuPage.deptColAccount')" prop="username"><el-input v-model="userForm.username" :placeholder="$t('message.menuPage.deptUserAccountPlaceholder')" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item :label="$t('message.menuPage.deptColName')" prop="name"><el-input v-model="userForm.name" :placeholder="$t('message.menuPage.deptUserNamePlaceholder')" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item :label="$t('message.menuPage.deptUserPhone')" prop="mobile"><el-input v-model="userForm.mobile" :placeholder="$t('message.menuPage.deptUserPhonePlaceholder')" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item :label="$t('message.menuPage.deptColEmail')" prop="email"><el-input v-model="userForm.email" :placeholder="$t('message.menuPage.deptUserEmailPlaceholder')" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item :label="$t('message.menuPage.deptColGender')"><el-select v-model="userForm.gender" :placeholder="$t('message.menuPage.deptUserGenderPlaceholder')" clearable><el-option v-for="g in genderOptions" :key="g.value" :label="g.label" :value="g.value" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item :label="$t('message.menuPage.deptUserType')"><el-select v-model="userForm.user_type" :placeholder="$t('message.menuPage.deptUserGenderPlaceholder')" clearable><el-option v-for="u in userTypeOptions" :key="u.value" :label="u.label" :value="u.value" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item :label="$t('message.menuPage.deptUserEnable')"><el-switch v-model="userForm.is_active" /></el-form-item></el-col>
          <el-col v-if="!isEditUser" :span="12"><el-form-item :label="$t('message.menuPage.deptUserPassword')" prop="password"><el-input v-model="userForm.password" type="password" show-password :placeholder="$t('message.menuPage.deptUserPasswordPlaceholder')" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button  @click="userDialogVisible = false">{{ $t('message.menuPage.deptUserCancel') }}</el-button>
        <el-button  type="primary" :loading="userBtnLoading" @click="handleUserSubmit">{{ $t('message.menuPage.deptUserSave') }}</el-button>
      </template>
    </el-dialog>

    <!-- ===== Reset Password Dialog ===== -->
    <el-dialog
      v-model="resetPwdVisible"
      :title="$t('message.menuPage.deptResetPwdTitle')"
      width="400px"
      :close-on-click-modal="false"
      @closed="handleResetPwdClose"
      class="opsflow-dialog"
    >
      <el-form ref="resetPwdFormRef" :model="resetPwdForm" :rules="resetPwdRules" label-width="90px" size="small">
        <el-form-item :label="$t('message.menuPage.deptNewPwd')" prop="newPassword">
          <el-input v-model="resetPwdForm.newPassword" type="password" show-password :placeholder="$t('message.menuPage.deptNewPwdPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('message.menuPage.deptConfirmPwd')" prop="newPassword2">
          <el-input v-model="resetPwdForm.newPassword2" type="password" show-password :placeholder="$t('message.menuPage.deptConfirmPwdPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button  @click="handleResetPwdClose">{{ $t('message.menuPage.deptResetPwdCancel') }}</el-button>
        <el-button  type="primary" :loading="resetPwdLoading" @click="handleResetPwdSubmit">{{ $t('message.menuPage.deptResetPwdConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup name="dept">
import { ref, reactive, computed, onMounted, nextTick, onUnmounted, markRaw } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessageBox, ElForm } from 'element-plus';
import {
  Plus, Refresh, Search,
  OfficeBuilding, User, Male, Female,
} from '@element-plus/icons-vue';
import { Md5 } from 'ts-md5';
import * as echarts from 'echarts';
import type { ECharts } from 'echarts';
import XEUtils from 'xe-utils';
import { request } from '/@/utils/service';
import { successNotification, warningNotification } from '/@/utils/message';


import DeptTreeCom from './components/DeptTreeCom/index.vue';
import DeptFormCom from './components/DeptFormCom/index.vue';
import { GetList, DelObj, getDeptUserList } from './api';
import {
  AddObj as AddUserObj, UpdateObj as UpdateUserObj,
  DelObj as DelUserObj, getDeptInfoById, resetPwd,
} from './components/DeptUserCom/api';
import type { APIResponseData, TreeItemType, HeadDeptInfoType } from './types';

/* ===================== Stats ===================== */
const { t } = useI18n();

const stats = computed(() => [
  { label: t('message.menuPage.deptTotal'), value: deptCount.value, icon: markRaw(OfficeBuilding), bg: 'linear-gradient(135deg,#409eff,#337ecc)' },
  { label: t('message.menuPage.deptCurrentMembers'), value: deptInfo.value.dept_user ?? '--', icon: markRaw(User), bg: 'linear-gradient(135deg,#67c23a,#409eff)' },
  { label: t('message.menuPage.deptMale'), value: deptInfo.value.gender?.male ?? '--', icon: markRaw(Male), bg: 'linear-gradient(135deg,#409eff,#667eea)' },
  { label: t('message.menuPage.deptFemale'), value: deptInfo.value.gender?.female ?? '--', icon: markRaw(Female), bg: 'linear-gradient(135deg,#f56c6c,#e6a23c)' },
]);
const deptCount = ref(0);

/* ===================== State ===================== */
const deptTreeData = ref<TreeItemType[]>([]);
const deptTreeCacheData = ref<TreeItemType[]>([]);
const drawerVisible = ref(false);
const drawerFormData = ref<Partial<TreeItemType>>({});
const deptTreeRef = ref<InstanceType<typeof DeptTreeCom> | null>(null);
const currentDeptName = ref('');

const deptInfo = ref<Partial<HeadDeptInfoType>>({});
const currentDeptId = ref('');
const isShowChildFlag = ref(false);
const deptCountBarRef = ref<HTMLElement | null>(null);
const deptSexPieRef = ref<HTMLElement | null>(null);
let deptCountChart: ECharts | null = null;
let deptSexChart: ECharts | null = null;

const userList = ref<any[]>([]);
const userLoading = ref(false);
const searchKeyword = ref('');
const pageParams = reactive({ current: 1, pageSize: 20, total: 0 });

const userDialogVisible = ref(false);
const isEditUser = ref(false);
const userBtnLoading = ref(false);
const userFormRef = ref<InstanceType<typeof ElForm> | null>(null);
const userForm = reactive<Record<string, any>>({
  username: '', name: '', mobile: '', email: '', gender: undefined,
  user_type: undefined, is_active: true, password: '', password2: '', id: undefined,
});
const userFormRules = {
  username: [{ required: true, message: t('message.menuPage.deptAccountRequired'), trigger: 'blur' }, { min: 3, max: 50, message: t('message.menuPage.deptAccountLen'), trigger: 'blur' }],
  name: [{ required: true, message: t('message.menuPage.deptNameInputRequired'), trigger: 'blur' }],
  mobile: [{ pattern: /^1[3-9]\d{9}$/, message: t('message.menuPage.deptPhoneInvalid'), trigger: 'blur' }],
  email: [{ type: 'email' as const, message: t('message.menuPage.deptPhoneInvalid'), trigger: 'blur' }],
  password: [{ required: true, message: t('message.menuPage.deptPwdRequired'), trigger: 'blur' }, { pattern: /(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}/, message: t('message.menuPage.deptPwdRule'), trigger: 'blur' }],
};

const resetPwdVisible = ref(false);
const resetPwdLoading = ref(false);
const resetPwdFormRef = ref<InstanceType<typeof ElForm> | null>(null);
const resetPwdForm = reactive({ id: 0, newPassword: '', newPassword2: '' });
const resetPwdRules = {
  newPassword: [{ required: true, message: t('message.menuPage.deptPwdRequired'), trigger: 'blur' }, { pattern: /(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}/, message: t('message.menuPage.deptPwdRule'), trigger: 'blur' }],
  newPassword2: [
    { required: true, message: t('message.menuPage.deptConfirmPwdRequired'), trigger: 'blur' },
    { validator: (_r: any, v: string, cb: Function) => v !== resetPwdForm.newPassword ? cb(new Error(t('message.menuPage.deptPwdMismatch'))) : cb(), trigger: 'blur' },
  ],
};

const genderOptions = ref<{ label: string; value: number }[]>([]);
const userTypeOptions = ref<{ label: string; value: number }[]>([]);
const roleOptions = ref<{ id: number; name: string }[]>([]);

/* ===================== Fetch ===================== */
const getData = async () => {
  const res: APIResponseData = await GetList({});
  if (res?.code === 2000 && Array.isArray(res.data)) {
    deptTreeData.value = XEUtils.toArrayTree(res.data, { parentKey: 'parent', children: 'children' });
    // Count all depts (flatten)
    const flat: any[] = [];
    const flatten = (arr: any[]) => { arr.forEach(i => { flat.push(i); if (i.children) flatten(i.children); }); };
    flatten(deptTreeData.value);
    deptCount.value = flat.length;
  }
};

const fetchRoles = async () => {
  try {
    const res = await request({ url: '/api/iam/role/', method: 'get', params: { page: 1, limit: 999 } });
    if (res?.code === 2000) roleOptions.value = Array.isArray(res.data) ? res.data : [];
  } catch { /* */ }
};
const loadDict = () => { genderOptions.value = []; userTypeOptions.value = []; };

/* ===================== Dept Tree Events ===================== */
const handleTreeClick = (record: TreeItemType) => {
  currentDeptId.value = String(record.id ?? '');
  currentDeptName.value = record.name || '';
  fetchUserList();
  fetchDeptInfo();
};

const handleDeleteMenu = (id: string, callback: Function) => {
  ElMessageBox.confirm(t('message.menuPage.deptConfirmDelete'), t('message.menuPage.deptConfirm'), { confirmButtonText: t('message.menuPage.deptDeleteBtn'), cancelButtonText: t('message.menuPage.deptCancelBtn'), type: 'warning' })
    .then(async () => {
      const res: APIResponseData = await DelObj(id);
      callback();
      if (res?.code === 2000) {
        successNotification(res.msg as string);
        getData();
        currentDeptId.value = '';
        userList.value = [];
      }
    }).catch(() => {});
};

const handleUpdateMenu = (type: string, record?: TreeItemType) => {
  if (type === 'update' && record) {
    const parentData = deptTreeRef.value?.treeRef?.currentNode.parent.data || {};
    deptTreeCacheData.value = [parentData];
    drawerFormData.value = record;
  }
  drawerVisible.value = true;
};

const handleDrawerClose = (type?: string) => {
  if (type === 'submit') getData();
  drawerVisible.value = false;
  drawerFormData.value = {};
};

/* ===================== Dept Info + Charts ===================== */
const fetchDeptInfo = async () => {
  if (!currentDeptId.value) { deptInfo.value = {}; return; }
  const res = await getDeptInfoById(currentDeptId.value, isShowChildFlag.value ? '1' : '0');
  if (res?.code === 2000) { deptInfo.value = res.data; await nextTick(); initCharts(); }
};

const initCharts = () => {
  if (!deptCountBarRef.value || !deptSexPieRef.value) return;
  // Bar
  if (!deptCountChart) deptCountChart = echarts.init(deptCountBarRef.value);
  deptCountChart.clear();
  deptCountChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 10, right: 10, bottom: 28, left: 36 },
    xAxis: { type: 'category', data: deptInfo.value.sub_dept_map?.map(i => i.name) || [], axisLabel: { fontSize: 10, rotate: 20 }, axisTick: { alignWithLabel: true } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { type: 'dashed', color: '#f0f0f0' } } },
    series: [{
      data: deptInfo.value.sub_dept_map?.map(i => i.count) || [], type: 'bar', barWidth: '50%',
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#83bff6' }, { offset: 1, color: '#188df0' }]), borderRadius: [4, 4, 0, 0] },
    }],
  });
  // Pie
  if (!deptSexChart) deptSexChart = echarts.init(deptSexPieRef.value);
  deptSexChart.clear();
  deptSexChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, left: 'center', itemWidth: 10, itemHeight: 10 },
    series: [{
      type: 'pie', radius: ['42%', '65%'], center: ['50%', '42%'],
      label: { show: false }, emphasis: { label: { show: true } },
      color: ['#188df0', '#f56c6c', '#dcdfe6'],
      data: [
        { value: deptInfo.value.gender?.male || 0, name: '男' },
        { value: deptInfo.value.gender?.female || 0, name: '女' },
        { value: deptInfo.value.gender?.unknown || 0, name: '未知' },
      ],
    }],
  });
};

const handleSwitchChange = () => { fetchUserList(); fetchDeptInfo(); };

/* ===================== User List ===================== */
const fetchUserList = async () => {
  if (!currentDeptId.value) { userList.value = []; pageParams.total = 0; return; }
  userLoading.value = true;
  try {
    const params: Record<string, any> = { page: pageParams.current, limit: pageParams.pageSize, dept: currentDeptId.value, show_all: isShowChildFlag.value ? '1' : '0' };
    if (searchKeyword.value.trim()) params.search = searchKeyword.value.trim();
    const res = await getDeptUserList(params);
    if (res?.code === 2000) { userList.value = res.data || []; pageParams.total = res.total || 0; }
  } finally { userLoading.value = false; }
};

const handlePageChange = () => fetchUserList();
const handleSearch = () => { pageParams.current = 1; fetchUserList(); };
const handleRefreshAll = () => { getData(); fetchUserList(); fetchDeptInfo(); };

const getRoleNames = (ids: number[] | undefined): string => {
  if (!ids?.length) return '-';
  return ids.map(id => roleOptions.value.find(r => r.id === id)?.name || String(id)).join(', ');
};
const displayGender = (val: number | null | undefined) => {
  if (val === null || val === undefined) return '-';
  return genderOptions.value.find(g => g.value === val)?.label || '-';
};

/* ===================== User CRUD ===================== */
const handleToggleActive = async (row: any) => {
  try { await UpdateUserObj({ id: row.id, is_active: row.is_active }); successNotification(t('message.menuPage.deptStatusUpdated')); }
  catch { row.is_active = !row.is_active; warningNotification(t('message.menuPage.deptUpdateFailed')); }
};

const resetUserForm = () => { Object.assign(userForm, { id: undefined, username: '', name: '', mobile: '', email: '', gender: undefined, user_type: undefined, is_active: true, password: '' }); };
const handleAddUser = () => { isEditUser.value = false; resetUserForm(); userDialogVisible.value = true; };
const handleEditUser = (row: any) => {
  isEditUser.value = true;
  Object.assign(userForm, { id: row.id, username: row.username, name: row.name, mobile: row.mobile || '', email: row.email || '', gender: row.gender, user_type: row.user_type, is_active: row.is_active, password: '' });
  userDialogVisible.value = true;
};

const handleUserSubmit = () => {
  userFormRef.value?.validate(async (valid: boolean) => {
    if (!valid) return;
    userBtnLoading.value = true;
    try {
      const payload: Record<string, any> = { username: userForm.username, name: userForm.name, mobile: userForm.mobile, email: userForm.email, gender: userForm.gender, user_type: userForm.user_type, is_active: userForm.is_active, dept: currentDeptId.value || undefined };
      if (!isEditUser.value && userForm.password) payload.password = Md5.hashStr(userForm.password);
      const res = isEditUser.value ? await UpdateUserObj({ id: userForm.id, ...payload }) : await AddUserObj(payload);
      if (res?.code === 2000) { successNotification(res.msg as string); userDialogVisible.value = false; fetchUserList(); fetchDeptInfo(); }
    } finally { userBtnLoading.value = false; }
  });
};
const handleUserDialogClose = () => { userFormRef.value?.resetFields(); resetUserForm(); };

const handleDeleteUser = (row: any) => {
  ElMessageBox.confirm(t('message.menuPage.deptDeleteUserConfirm') + `「${row.name || row.username}」？`, '确认', { confirmButtonText: t('message.menuPage.deptDeleteBtn'), cancelButtonText: t('message.menuPage.deptCancelBtn'), type: 'warning' })
    .then(async () => {
      const res = await DelUserObj(row.id);
      if (res?.code === 2000) { successNotification(res.msg as string); fetchUserList(); fetchDeptInfo(); }
    }).catch(() => {});
};

/* ===================== Reset Password ===================== */
const handleResetPwdOpen = (row: any) => { resetPwdForm.id = row.id; resetPwdVisible.value = true; };
const handleResetPwdClose = () => { resetPwdFormRef.value?.resetFields(); resetPwdForm.id = 0; resetPwdForm.newPassword = ''; resetPwdForm.newPassword2 = ''; resetPwdVisible.value = false; };
const handleResetPwdSubmit = () => {
  resetPwdFormRef.value?.validate(async (valid: boolean) => {
    if (!valid) return;
    resetPwdLoading.value = true;
    try {
      const res = await resetPwd(resetPwdForm.id, { newPassword: Md5.hashStr(resetPwdForm.newPassword), newPassword2: Md5.hashStr(resetPwdForm.newPassword2) });
      if (res?.code === 2000) { successNotification(res.msg || t('message.menuPage.deptPwdChanged')); handleResetPwdClose(); }
    } finally { resetPwdLoading.value = false; }
  });
};

/* ===================== Lifecycle ===================== */
onMounted(() => { getData(); fetchRoles(); loadDict(); });
onUnmounted(() => { deptCountChart?.dispose(); deptSexChart?.dispose(); });
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;

.dept-page { width: 100%; }

// ===== Stats =====
.dept-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}
.dept-stat-card {
  display: flex; align-items: center; gap: 14px;
  background: #fff; border-radius: $g-radius; padding: 16px 18px;
  box-shadow: $g-shadow-card; transition: transform .2s, box-shadow .2s;
  cursor: default;
  &:hover { transform: translateY(-2px); box-shadow: $g-shadow-hover; }
}
.dept-stat-icon {
  width: 42px; height: 42px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0; color: #fff;
}
.dept-stat-body { flex: 1; min-width: 0; }
.dept-stat-val { font-size: 22px; font-weight: 700; color: $g-text-primary; line-height: 1.2; }
.dept-stat-lbl { font-size: 13px; color: $g-text-secondary; margin-top: 2px; }

// ===== Layout =====
.dept-main-row {
  height: calc(100vh - 185px);
  overflow: hidden;
  .el-col { height: 100%; }
}
.dept-tree-wrap { height: 100%; overflow: hidden; }
.dept-content {
  height: 100%; display: flex; flex-direction: column; overflow: hidden;
  padding: 0; box-sizing: border-box;
}

// ===== Empty =====
.dept-empty {
  flex: 1; display: flex; align-items: center; justify-content: center;
}

// ===== Breadcrumb Header =====
.dept-bread {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 18px 10px;
  border-bottom: 1px solid $g-border-light;
  flex-shrink: 0;
}
.dept-bread-name {
  font-size: 16px; font-weight: 600; color: $g-text-primary;
}
.dept-bread-tag { margin-left: 2px; }
.dept-bread-switch {
  margin-left: auto;
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: $g-text-secondary;
}

// ===== Dashboard (info + charts) =====
.dept-dashboard {
  display: flex; align-items: stretch; gap: 0;
  padding: 14px 18px;
  background: $g-gradient-hero;
  border-bottom: 1px solid $g-border-light;
  flex-shrink: 0;
}
.dept-dash-info {
  display: flex; flex-direction: column; justify-content: center; gap: 6px;
  min-width: 160px; flex-shrink: 0;
  padding-right: 18px;
  border-right: 1px solid $g-border-light;
}
.dept-info-row {
  display: flex; align-items: center; gap: 8px; font-size: 13px;
  .dept-info-label { color: $g-text-secondary; min-width: 56px; }
  .dept-info-val { color: $g-text-regular; font-weight: 500; }
  .dept-info-desc { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
}
.dept-dash-charts {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 12px;
  padding-left: 14px;
}
.dept-chart { flex-shrink: 0; }
.dept-chart-bar { width: 340px; height: 130px; }
.dept-chart-pie { width: 160px; height: 130px; }

// ===== Toolbar =====
.dept-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 18px; flex-shrink: 0;
  border-bottom: 1px solid $g-border-light;
  .dept-toolbar-left, .dept-toolbar-right { display: flex; align-items: center; gap: 8px; }
}

// ===== Pagination =====
.dept-pagination {
  display: flex; justify-content: flex-end;
  padding: 10px 18px; flex-shrink: 0;
  border-top: 1px solid $g-border-light;
}

// ===== Responsive =====
@media screen and (max-width: 1200px) {
  .dept-dashboard { flex-direction: column; align-items: stretch; }
  .dept-dash-info { border-right: none; border-bottom: 1px solid $g-border-light; padding: 0 0 10px; }
  .dept-dash-charts { padding: 10px 0 0; }
  .dept-chart-bar { width: 260px; }
}
</style>
