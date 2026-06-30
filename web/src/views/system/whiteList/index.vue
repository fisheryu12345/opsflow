<template>
  <div class="sys-page sys-fade-in-up">
    <!-- ===== Stats Cards ===== -->
    <div class="wl-stats">
      <div v-for="s in stats" :key="s.label" class="wl-stat-card">
        <div class="wl-stat-icon" :style="{ background: s.bg }">
          <el-icon :size="20"><component :is="s.icon" /></el-icon>
        </div>
        <div class="wl-stat-body">
          <div class="wl-stat-val">{{ s.value }}</div>
          <div class="wl-stat-lbl">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <!-- ===== Main Card ===== -->
    <div class="sys-card sys-fade-in-up" style="animation-delay:0.08s">
      <div class="sys-card-header">
        <div class="sys-card-title">
          <span class="sys-card-icon"><el-icon :size="16"><Lock /></el-icon></span>
          <span>接口白名单</span>
        </div>
        <div class="sys-card-extra">
          <el-button type="primary" size="small" :icon="Plus" @click="handleAdd">新增</el-button>
        </div>
      </div>

      <div class="sys-card-body">
        <!-- Toolbar -->
        <div class="wl-toolbar">
          <el-form :inline="true" :model="searchParams" size="small">
            <el-form-item label="请求方式">
              <el-select v-model="searchParams.method" clearable placeholder="全部" style="width:140px">
                <el-option v-for="opt in methodOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="small" @click="handleSearch">查询</el-button>
              <el-button :icon="Refresh" size="small" @click="handleReset">重置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- Table -->
        <el-table :data="state.data" v-loading="state.loading" stripe size="small" style="width:100%" row-key="id">
          <el-table-column label="#" width="55" align="center">
            <template #default="scope">{{ ((searchParams.page - 1) * searchParams.limit) + scope.$index + 1 }}</template>
          </el-table-column>
          <el-table-column prop="method" label="请求方式" width="110" align="center">
            <template #default="scope">
              <el-tag :type="methodTagType(scope.row.method)" effect="dark" size="small">{{ methodLabel(scope.row.method) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="url" label="接口地址" min-width="280" show-overflow-tooltip>
            <template #default="scope">
              <code class="wl-url-code">{{ scope.row.url }}</code>
            </template>
          </el-table-column>
          <el-table-column label="数据权限" width="120" align="center">
            <template #default="scope">
              <el-switch v-model="scope.row.enable_datasource" size="small" @change="handleSwitchChange(scope.row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right" align="center">
            <template #default="scope">
              <el-button text size="small" style="padding:0 4px" @click="handleEdit(scope.row)">编辑</el-button>
              <el-button text type="danger" size="small" style="padding:0 4px" @click="handleDelete(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="wl-pagination">
          <el-pagination v-model:currentPage="searchParams.page" v-model:pageSize="searchParams.limit" :total="state.total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next, jumper" background size="small" @update:pageSize="handleSizeChange" @update:currentPage="handleCurrentChange" />
        </div>
      </div>
    </div>

    <!-- ===== Dialog ===== -->
    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增白名单' : '编辑白名单'" width="560px" :close-on-click-modal="false" @open="handleDialogOpen" @close="handleDialogClose" class="opsflow-dialog">
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px" size="small">
        <el-form-item label="请求方式" prop="method">
          <el-select v-model="formData.method" placeholder="请选择" style="width:100%">
            <el-option v-for="opt in methodOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="接口地址" prop="url">
          <el-autocomplete v-model="formData.url" :fetch-suggestions="queryUrlSuggestions" :trigger-on-focus="true" allow-create filterable clearable placeholder="输入接口地址或选择" style="width:100%">
            <template #default="{ item }"><code class="wl-url-code">{{ item.value }}</code></template>
          </el-autocomplete>
          <div class="wl-form-tip">匹配单例使用正则，例如：<code>/api/xx/.*?</code></div>
        </el-form-item>
        <el-form-item label="数据权限" prop="enable_datasource">
          <el-radio-group v-model="formData.enable_datasource">
            <el-radio :value="false">禁用</el-radio>
            <el-radio :value="true">启用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button  @click="dialogVisible = false">取消</el-button>
        <el-button  type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts" name="whiteList">
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessageBox } from 'element-plus';
import { Plus, Lock, Tickets, Check, Close } from '@element-plus/icons-vue';

import { successMessage } from '/@/utils/message';
import { request } from '/@/utils/service';
import * as api from './api';
import type { FormInstance } from 'element-plus';

/* ===================== Dict ===================== */
const methodOptions = [
  { label: 'GET', value: 0 }, { label: 'POST', value: 1 },
  { label: 'PUT', value: 2 }, { label: 'DELETE', value: 3 }, { label: 'PATCH', value: 4 },
];
const methodLabels: Record<number, string> = { 0: 'GET', 1: 'POST', 2: 'PUT', 3: 'DELETE', 4: 'PATCH' };
const methodTagTypes: Record<number, string> = { 0: 'success', 1: 'primary', 2: 'warning', 3: 'danger', 4: 'info' };
function methodLabel(v: number) { return methodLabels[v] ?? 'GET'; }
function methodTagType(v: number) { return methodTagTypes[v] ?? ''; }

/* ===================== Stats ===================== */
const stats = computed(() => [
  { label: '白名单总数', value: state.total, icon: Tickets, bg: 'linear-gradient(135deg,#409eff,#337ecc)' },
  { label: 'GET', value: state.data.filter((r: any) => r.method === 0).length, icon: Check, bg: 'linear-gradient(135deg,#67c23a,#409eff)' },
  { label: 'POST/PUT', value: state.data.filter((r: any) => r.method === 1 || r.method === 2).length, icon: Lock, bg: 'linear-gradient(135deg,#e6a23c,#f56c6c)' },
  { label: 'DELETE', value: state.data.filter((r: any) => r.method === 3).length, icon: Close, bg: 'linear-gradient(135deg,#f56c6c,#e6a23c)' },
]);

/* ===================== State ===================== */
const searchParams = reactive({ page: 1, limit: 10, method: undefined as number | undefined });
const state = reactive({ loading: false, data: [] as any[], total: 0 });
const dialogVisible = ref(false);
const dialogType = ref<'add' | 'edit'>('add');
const submitLoading = ref(false);
const formRef = ref<FormInstance>();
const defaultForm = { method: 0, url: '', enable_datasource: false };
const formData = reactive({ ...defaultForm });
const formRules = { method: [{ required: true, message: '必填项', trigger: 'change' }], url: [{ required: true, message: '必填项', trigger: 'blur' }] };

/* ===================== Swagger ===================== */
let swaggerUrls: string[] = [];
async function ensureSwaggerLoaded() {
  if (swaggerUrls.length > 0) return;
  try { const res: any = await request('/api/schema/'); swaggerUrls = Object.keys(res.paths || {}); }
  catch { swaggerUrls = []; }
}
function queryUrlSuggestions(queryString: string, callback: (results: { value: string }[]) => void) {
  callback(swaggerUrls.filter(p => p.includes(queryString)).map(p => ({ value: p })));
}

/* ===================== CRUD ===================== */
async function fetchData() {
  state.loading = true;
  try {
    const res: any = await api.GetList({ page: searchParams.page, limit: searchParams.limit, method: searchParams.method });
    if (res?.code === 2000) { state.data = res.data || []; state.total = res.total || 0; }
  } finally { state.loading = false; }
}
function handleSearch() { searchParams.page = 1; fetchData(); }
function handleReset() { searchParams.page = 1; searchParams.method = undefined; fetchData(); }
function handleSizeChange(limit: number) { searchParams.limit = limit; fetchData(); }
function handleCurrentChange(page: number) { searchParams.page = page; fetchData(); }

function handleAdd() { dialogType.value = 'add'; Object.assign(formData, defaultForm); dialogVisible.value = true; }
function handleEdit(row: any) {
  dialogType.value = 'edit';
  formData.id = row.id; formData.method = row.method; formData.url = row.url; formData.enable_datasource = row.enable_datasource;
  dialogVisible.value = true;
}
async function handleDialogOpen() { await ensureSwaggerLoaded(); }
function handleDialogClose() { dialogVisible.value = false; formRef.value?.resetFields(); }

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitLoading.value = true;
  try {
    const payload = { method: formData.method, url: formData.url, enable_datasource: formData.enable_datasource };
    const res = dialogType.value === 'add' ? await api.AddObj(payload) : await api.UpdateObj({ ...payload, id: formData.id });
    if (res?.code === 2000) { successMessage(res.msg || '操作成功'); dialogVisible.value = false; fetchData(); }
  } finally { submitLoading.value = false; }
}

function handleDelete(row: any) {
  ElMessageBox.confirm('确定删除该白名单记录？', '确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    .then(async () => { const res = await api.DelObj(row.id); if (res?.code === 2000) { successMessage(res.msg || '删除成功'); fetchData(); } })
    .catch(() => {});
}

async function handleSwitchChange(row: any) {
  const res = await api.UpdateObj(row);
  if (res?.code === 2000) successMessage(res.msg || '更新成功');
}

onMounted(() => { fetchData(); });
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;

// ===== Stats =====
.wl-stats {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px; margin-bottom: 16px;
}
.wl-stat-card {
  display: flex; align-items: center; gap: 14px;
  background: #fff; border-radius: $g-radius; padding: 16px 18px;
  box-shadow: $g-shadow-card; transition: transform .2s, box-shadow .2s;
  cursor: default;
  &:hover { transform: translateY(-2px); box-shadow: $g-shadow-hover; }
}
.wl-stat-icon { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; color: #fff; }
.wl-stat-body { flex: 1; min-width: 0; }
.wl-stat-val { font-size: 22px; font-weight: 700; color: $g-text-primary; line-height: 1.2; }
.wl-stat-lbl { font-size: 13px; color: $g-text-secondary; margin-top: 2px; }

// ===== Page =====
.g-page { width: 100%; }

// ===== Toolbar =====
.wl-toolbar { margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid $g-border-light; }
.wl-toolbar :deep(.el-form--inline .el-form-item) { margin-right: 14px; margin-bottom: 0; }

// ===== URL Code =====
.wl-url-code { font-size: 12px; font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace; background: $g-bg-page; padding: 2px 6px; border-radius: 4px; color: $g-text-regular; }

// ===== Pagination =====
.wl-pagination { display: flex; justify-content: flex-end; padding-top: 14px; margin-top: 4px; border-top: 1px solid $g-border-light; }

// ===== Form =====
.wl-form-tip { margin-top: 4px; font-size: 12px; color: $g-text-secondary; line-height: 1.4; code { font-size: 11px; background: $g-bg-page; padding: 1px 4px; border-radius: 3px; } }
</style>
