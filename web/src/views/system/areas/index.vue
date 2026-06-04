<template>
  <div class="sys-page">
    <!-- Stats Cards Row -->
    <div class="stats-row sys-fade-in-up">
      <div class="sys-card stats-card sys-hover-lift">
        <div class="stats-inner">
          <div class="stats-icon" style="background: linear-gradient(135deg, #409eff, #337ecc)">
            <el-icon><List /></el-icon>
          </div>
          <div class="stats-info">
            <p class="stats-value">{{ stats.total }}</p>
            <p class="stats-label">地区总数</p>
          </div>
        </div>
      </div>
      <div class="sys-card stats-card sys-hover-lift">
        <div class="stats-inner">
          <div class="stats-icon" style="background: linear-gradient(135deg, #67c23a, #409eff)">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="stats-info">
            <p class="stats-value">{{ stats.enabled }}</p>
            <p class="stats-label">已启用</p>
          </div>
        </div>
      </div>
      <div class="sys-card stats-card sys-hover-lift">
        <div class="stats-inner">
          <div class="stats-icon" style="background: linear-gradient(135deg, #f56c6c, #e6a23c)">
            <el-icon><CircleClose /></el-icon>
          </div>
          <div class="stats-info">
            <p class="stats-value">{{ stats.disabled }}</p>
            <p class="stats-label">已禁用</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Table Card -->
    <div class="sys-card sys-fade-in-up" style="margin-top: 16px; animation-delay: 0.1s">
      <!-- Card Header with Search and Add -->
      <div class="sys-card-header">
        <div class="sys-card-title">
          <span class="sys-card-icon">
            <el-icon><Grid /></el-icon>
          </span>
          <span>地区管理</span>
        </div>
        <div class="sys-card-extra">
          <el-form :model="searchForm" inline size="small" @keyup.enter="handleSearch">
            <el-form-item>
              <el-input v-model="searchForm.name" placeholder="名称" clearable />
            </el-form-item>
            <el-form-item>
              <el-input v-model="searchForm.code" placeholder="地区编码" clearable />
            </el-form-item>
            <el-form-item>
              <el-input v-model="searchForm.pinyin" placeholder="拼音" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearch">搜索</el-button>
              <el-button @click="handleReset">重置</el-button>
            </el-form-item>
          </el-form>
          <el-button v-if="auth('area:Create')" type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>新增地区
          </el-button>
        </div>
      </div>

      <!-- Table Body -->
      <div class="sys-card-body" style="padding: 0">
        <el-table
          :data="tableData"
          row-key="id"
          lazy
          :load="loadChildren"
          :tree-props="{ children: 'children', hasChildren: 'hasChild' }"
          v-loading="loading"
          stripe
          border
          style="width: 100%"
        >
          <el-table-column type="index" label="序号" width="70" align="center" />
          <el-table-column prop="name" label="名称" tree-node min-width="140" show-overflow-tooltip />
          <el-table-column prop="code" label="地区编码" width="110" />
          <el-table-column prop="pinyin" label="拼音" min-width="130" />
          <el-table-column prop="level" label="地区层级" width="100" />
          <el-table-column prop="initials" label="首字母" width="90" />
          <el-table-column label="是否启用" width="120" align="center">
            <template #default="{ row }">
              <el-switch
                v-model="row.enable"
                :loading="row._switchLoading"
                @change="(val: boolean) => handleEnableToggle(row, val)"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" fixed="right" width="200" align="center">
            <template #default="{ row }">
              <el-button
                v-if="auth('area:Update')"
                type="primary"
                link
                size="small"
                @click="handleEdit(row)"
              >
                <el-icon><Edit /></el-icon>编辑
              </el-button>
              <el-button
                v-if="auth('area:Delete')"
                type="danger"
                link
                size="small"
                @click="handleDelete(row)"
              >
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :description="loading ? '加载中...' : '暂无数据'" />
          </template>
        </el-table>
      </div>
    </div>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑地区' : '新增地区'"
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
      :before-close="handleDialogClose"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px" size="default">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="地区编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入地区编码" maxlength="20" />
        </el-form-item>
        <el-form-item label="拼音" prop="pinyin">
          <el-input v-model="form.pinyin" placeholder="请输入拼音" maxlength="255" />
        </el-form-item>
        <el-form-item label="地区层级" prop="level">
          <el-input-number
            v-model="form.level"
            :min="1"
            :max="4"
            :value-on-clear="1"
            placeholder="地区层级"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="首字母" prop="initials">
          <el-input v-model="form.initials" placeholder="请输入首字母" maxlength="20" />
        </el-form-item>
        <el-form-item label="是否启用" prop="enable">
          <el-radio-group v-model="form.enable">
            <el-radio :value="true">启用</el-radio>
            <el-radio :value="false">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup name="areas">
import { ref, reactive, computed, onMounted } from 'vue';
import type { FormInstance } from 'element-plus';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Plus,
  Edit,
  Delete,
  Grid,
  List,
  CircleCheck,
  CircleClose,
} from '@element-plus/icons-vue';
import { auth } from '/@/utils/authFunction';
import * as api from './api';

/** Area data item from the API */
interface AreaItem {
  id?: number;
  name: string;
  code: string;
  pinyin: string;
  level: number;
  initials: string;
  enable: boolean;
  pcode?: string | null;
  hasChild?: boolean;
  children?: AreaItem[];
  _switchLoading?: boolean;
}

// ── State ──────────────────────────────────────────────
const tableData = ref<AreaItem[]>([]);
const loading = ref(false);
const submitLoading = ref(false);
const dialogVisible = ref(false);
const isEdit = ref(false);
const formRef = ref<FormInstance>();

const searchForm = reactive({
  name: '',
  code: '',
  pinyin: '',
});

const form = reactive<Partial<AreaItem>>({
  name: '',
  code: '',
  pinyin: '',
  level: 1,
  initials: '',
  enable: true,
  pcode: null,
  id: undefined,
});

const formRules = {
  name: [{ required: true, message: '名称为必填项', trigger: 'blur' }],
  code: [{ required: true, message: '地区编码为必填项', trigger: 'blur' }],
  pinyin: [{ required: true, message: '拼音为必填项', trigger: 'blur' }],
  level: [{ required: true, message: '地区层级为必填项', trigger: 'blur' }],
  initials: [{ required: true, message: '首字母为必填项', trigger: 'blur' }],
};

// ── Computed ───────────────────────────────────────────
/** Recursively flatten tree into a flat array for stats */
function flattenTree(nodes: AreaItem[]): AreaItem[] {
  const result: AreaItem[] = [];
  for (const n of nodes) {
    result.push(n);
    if (n.children && n.children.length) {
      result.push(...flattenTree(n.children));
    }
  }
  return result;
}

const stats = computed(() => {
  const all = flattenTree(tableData.value);
  return {
    total: all.length,
    enabled: all.filter((n) => n.enable === true).length,
    disabled: all.filter((n) => n.enable === false).length,
  };
});

// ── Data fetching ──────────────────────────────────────
async function fetchData() {
  loading.value = true;
  try {
    const params: Record<string, string> = {};
    if (searchForm.name) params.name = searchForm.name;
    if (searchForm.code) params.code = searchForm.code;
    if (searchForm.pinyin) params.pinyin = searchForm.pinyin;
    const res: any = await api.GetList(params);
    if (res.code === 2000) {
      tableData.value = res.data || [];
    }
  } catch {
    // Error notification handled by Axios interceptor
  } finally {
    loading.value = false;
  }
}

/** Lazy-load children when a tree node is expanded */
const loadChildren = async (
  row: AreaItem,
  _treeNode: any,
  resolve: (data: AreaItem[]) => void,
) => {
  try {
    const res: any = await api.GetList({ pcode: row.code });
    if (res.code === 2000) {
      resolve(res.data || []);
    } else {
      resolve([]);
    }
  } catch {
    resolve([]);
  }
};

// ── Search ─────────────────────────────────────────────
function handleSearch() {
  fetchData();
}

function handleReset() {
  searchForm.name = '';
  searchForm.code = '';
  searchForm.pinyin = '';
  fetchData();
}

// ── Add / Edit dialog ──────────────────────────────────
function resetForm(data?: Partial<AreaItem>) {
  form.name = data?.name ?? '';
  form.code = data?.code ?? '';
  form.pinyin = data?.pinyin ?? '';
  form.level = data?.level ?? 1;
  form.initials = data?.initials ?? '';
  form.enable = data?.enable ?? true;
  form.pcode = data?.pcode ?? null;
  form.id = data?.id ?? undefined;
}

function handleAdd() {
  isEdit.value = false;
  resetForm();
  dialogVisible.value = true;
}

function handleEdit(row: AreaItem) {
  isEdit.value = true;
  resetForm(row);
  dialogVisible.value = true;
}

function handleDialogClose(done: () => void) {
  formRef.value?.resetFields();
  done();
}

// ── Submit ─────────────────────────────────────────────
async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitLoading.value = true;
  try {
    let res: any;
    if (isEdit.value) {
      res = await api.UpdateObj({ ...form, id: form.id! });
    } else {
      res = await api.AddObj(form);
    }
    if (res.code === 2000) {
      ElMessage.success(res.msg || (isEdit.value ? '更新成功' : '新增成功'));
      dialogVisible.value = false;
      await fetchData();
    }
  } catch {
    // Error notification handled by Axios interceptor
  } finally {
    submitLoading.value = false;
  }
}

// ── Delete ─────────────────────────────────────────────
function handleDelete(row: AreaItem) {
  ElMessageBox.confirm('您确认删除该地区吗?', '温馨提示', {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        const res: any = await api.DelObj(row.id!);
        if (res.code === 2000) {
          ElMessage.success(res.msg || '删除成功');
          await fetchData();
        }
      } catch {
        // Error notification handled by Axios interceptor
      }
    })
    .catch(() => {});
}

// ── Enable toggle (inline update) ──────────────────────
async function handleEnableToggle(row: AreaItem, val: boolean) {
  const oldVal = row.enable;
  row.enable = val; // immediate visual feedback
  row._switchLoading = true;
  try {
    const res: any = await api.UpdateObj({ id: row.id, enable: val });
    if (res.code !== 2000) {
      row.enable = oldVal; // revert on failure
    }
  } catch {
    row.enable = oldVal; // revert on network error
  } finally {
    row._switchLoading = false;
  }
}

// ── Lifecycle ──────────────────────────────────────────
onMounted(() => {
  fetchData();
});
</script>

<style lang="scss" scoped>
@use '../styles/system-global' as *;

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stats-card {
  padding: 16px 20px;
}

.stats-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stats-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  flex-shrink: 0;
}

.stats-info {
  flex: 1;
}

.stats-value {
  font-size: 26px;
  font-weight: 700;
  color: $sys-text-primary;
  margin: 0;
  line-height: 1.2;
}

.stats-label {
  font-size: 13px;
  color: $sys-text-secondary;
  margin: 4px 0 0;
}

// ── Override default form gap for inline search bar ──
:deep(.el-form--inline) {
  flex-wrap: nowrap;

  .el-form-item {
    margin-right: 6px;
    margin-bottom: 0;
  }
}
</style>
