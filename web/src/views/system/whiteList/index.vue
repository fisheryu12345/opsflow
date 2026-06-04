<template>
  <div class="whitelist-page">
    <!-- Search bar -->
    <div class="of-card whitelist-search">
      <el-form :inline="true" :model="searchParams" @keyup.enter="handleSearch">
        <el-form-item label="请求方式" prop="method">
          <el-select v-model="searchParams.method" clearable placeholder="请选择请求方式" style="width:160px">
            <el-option v-for="opt in methodOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- Table card -->
    <div class="of-card whitelist-table">
      <!-- Action bar -->
      <div class="whitelist-actionbar">
        <el-button v-if="auth('api_white_list:Create')" type="primary" @click="handleAdd">
          <el-icon style="margin-right:4px"><Plus /></el-icon>新增
        </el-button>
      </div>

      <el-table :data="state.data" border v-loading="state.loading" style="width:100%">
        <el-table-column label="序号" width="70" align="center">
          <template #default="scope">
            {{ ((searchParams.page - 1) * searchParams.limit) + scope.$index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="method" label="请求方式" width="120" align="center">
          <template #default="scope">
            <el-tag :type="methodTagType(scope.row.method)" effect="plain" size="small">
              {{ methodLabel(scope.row.method) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="url" label="接口地址" min-width="200" show-overflow-tooltip />
        <el-table-column label="数据权限认证" width="140" align="center">
          <template #default="scope">
            <el-switch
              v-model="scope.row.enable_datasource"
              inline-prompt
              active-text=""
              inactive-text=""
              :style="switchStyle"
              @change="handleSwitchChange(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="scope">
            <el-button v-if="auth('api_white_list:Update')" type="primary" link size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button v-if="auth('api_white_list:Delete')" type="danger" link size="small" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="whitelist-pagination">
        <el-pagination
          v-model:current-page="searchParams.page"
          v-model:page-size="searchParams.limit"
          :page-sizes="[10, 20, 50, 100]"
          :total="state.total"
          background
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- Add / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '新增白名单' : '编辑白名单'"
      width="600px"
      class="opsflow-dialog whitelist-dialog"
      :close-on-click-modal="false"
      @open="handleDialogOpen"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="110px"
      >
        <el-form-item label="请求方式" prop="method">
          <el-select v-model="formData.method" placeholder="请选择请求方式" style="width:100%">
            <el-option v-for="opt in methodOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="接口地址" prop="url">
          <el-autocomplete
            v-model="formData.url"
            :fetch-suggestions="queryUrlSuggestions"
            :trigger-on-focus="true"
            allow-create
            filterable
            clearable
            placeholder="请输入接口地址"
            style="width:100%"
          >
            <template #default="{ item }">
              <span class="url-suggestion-text">{{ item.value }}</span>
            </template>
          </el-autocomplete>
          <div class="whitelist-form-helper">
            请正确填写，以免请求时被拦截。匹配单例使用正则,例如:/api/xx/.*?/
          </div>
        </el-form-item>
        <el-form-item label="数据权限认证" prop="enable_datasource">
          <el-radio-group v-model="formData.enable_datasource">
            <el-radio :value="false">禁用</el-radio>
            <el-radio :value="true">启用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts" name="whiteList">
import { ref, reactive, onMounted } from 'vue';
import { ElMessageBox } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import { auth } from '/@/utils/authFunction';
import { successMessage } from '/@/utils/message';
import { request } from '/@/utils/service';
import * as api from './api';
import type { FormInstance } from 'element-plus';

/* ------------------------------------------------------------------ */
/*  Dict / constants                                                   */
/* ------------------------------------------------------------------ */

/** method 字典: 0=GET, 1=POST, 2=PUT, 3=DELETE, 4=PATCH */
const methodOptions = [
  { label: 'GET', value: 0 },
  { label: 'POST', value: 1 },
  { label: 'PUT', value: 2 },
  { label: 'DELETE', value: 3 },
  { label: 'PATCH', value: 4 },
];

const methodLabels: Record<number, string> = {
  0: 'GET',
  1: 'POST',
  2: 'PUT',
  3: 'DELETE',
  4: 'PATCH',
};

const methodTagTypes: Record<number, string> = {
  0: 'success',
  1: 'primary',
  2: 'warning',
  3: 'danger',
  4: 'info',
};

const switchStyle =
  '--el-switch-on-color: var(--el-color-primary); --el-switch-off-color: #dcdfe6';

function methodLabel(v: number): string {
  return methodLabels[v] ?? 'GET';
}
function methodTagType(v: number): string {
  return methodTagTypes[v] ?? '';
}

/* ------------------------------------------------------------------ */
/*  State                                                              */
/* ------------------------------------------------------------------ */

const searchParams = reactive({
  page: 1,
  limit: 10,
  method: undefined as number | undefined,
});

const state = reactive({
  loading: false,
  data: [] as any[],
  total: 0,
});

const dialogVisible = ref(false);
const dialogType = ref<'add' | 'edit'>('add');
const submitLoading = ref(false);
const formRef = ref<FormInstance>();

const defaultFormData = {
  method: 0,
  url: '',
  enable_datasource: false,
};

const formData = reactive({ ...defaultFormData });

const formRules: Record<string, any> = {
  method: [{ required: true, message: '必填项', trigger: 'change' }],
  url: [{ required: true, message: '必填项', trigger: 'blur' }],
};

/* ------------------------------------------------------------------ */
/*  Swagger URL autocomplete cache                                     */
/* ------------------------------------------------------------------ */

let swaggerUrls: string[] = [];

async function ensureSwaggerLoaded() {
  if (swaggerUrls.length > 0) return;
  try {
    const res: any = await request('/swagger.json');
    swaggerUrls = Object.keys(res.paths || {});
  } catch {
    swaggerUrls = [];
  }
}

function queryUrlSuggestions(queryString: string, callback: (results: { value: string }[]) => void) {
  const results = swaggerUrls
    .filter((path) => path.includes(queryString))
    .map((path) => ({ value: path }));
  callback(results);
}

/* ------------------------------------------------------------------ */
/*  CRUD                                                               */
/* ------------------------------------------------------------------ */

async function fetchData() {
  state.loading = true;
  try {
    const res: any = await api.GetList({
      page: searchParams.page,
      limit: searchParams.limit,
      method: searchParams.method,
    });
    if (res?.code === 2000) {
      state.data = res.data || [];
      state.total = res.total || 0;
    }
  } finally {
    state.loading = false;
  }
}

/* -- Search -------------------------------------------------------- */

function handleSearch() {
  searchParams.page = 1;
  fetchData();
}

function handleReset() {
  searchParams.page = 1;
  searchParams.method = undefined;
  fetchData();
}

/* -- Pagination ---------------------------------------------------- */

function handleSizeChange(limit: number) {
  searchParams.limit = limit;
  fetchData();
}

function handleCurrentChange(page: number) {
  searchParams.page = page;
  fetchData();
}

/* -- Add ----------------------------------------------------------- */

function handleAdd() {
  dialogType.value = 'add';
  Object.assign(formData, defaultFormData);
  dialogVisible.value = true;
}

/* -- Edit ---------------------------------------------------------- */

function handleEdit(row: any) {
  dialogType.value = 'edit';
  formData.id = row.id;
  formData.method = row.method;
  formData.url = row.url;
  formData.enable_datasource = row.enable_datasource;
  dialogVisible.value = true;
}

/* -- Dialog lifecycle ---------------------------------------------- */

async function handleDialogOpen() {
  await ensureSwaggerLoaded();
}

function handleDialogClose() {
  dialogVisible.value = false;
  formRef.value?.resetFields();
}

/* -- Submit -------------------------------------------------------- */

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  submitLoading.value = true;
  try {
    const payload: any = {
      method: formData.method,
      url: formData.url,
      enable_datasource: formData.enable_datasource,
    };

    let res: any;
    if (dialogType.value === 'add') {
      res = await api.AddObj(payload);
    } else {
      payload.id = formData.id;
      res = await api.UpdateObj(payload);
    }

    if (res?.code === 2000) {
      successMessage(res.msg || (dialogType.value === 'add' ? '新增成功' : '更新成功'));
      dialogVisible.value = false;
      fetchData();
    }
  } finally {
    submitLoading.value = false;
  }
}

/* -- Delete -------------------------------------------------------- */

function handleDelete(row: any) {
  ElMessageBox.confirm('确定删除该白名单记录吗？', '提示', {
    type: 'warning',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  })
    .then(async () => {
      const res: any = await api.DelObj(row.id);
      if (res?.code === 2000) {
        successMessage(res.msg || '删除成功');
        fetchData();
      }
    })
    .catch(() => {
      /* cancelled */
    });
}

/* -- Inline switch update ------------------------------------------ */

async function handleSwitchChange(row: any) {
  const res: any = await api.UpdateObj(row);
  if (res?.code === 2000) {
    successMessage(res.msg || '更新成功');
  }
}

/* ------------------------------------------------------------------ */
/*  Bootstrap                                                          */
/* ------------------------------------------------------------------ */

onMounted(() => {
  fetchData();
});
</script>

<style lang="scss" scoped>
.whitelist-page {
  padding: 16px;

  .whitelist-search {
    margin-bottom: 16px;
    padding-bottom: 0;
  }

  .whitelist-table {
    .whitelist-actionbar {
      margin-bottom: 12px;
    }

    .whitelist-pagination {
      margin-top: 14px;
      display: flex;
      justify-content: flex-end;
    }
  }

  .url-suggestion-text {
    font-family: 'Courier New', Courier, monospace;
    font-size: 13px;
  }

  .whitelist-form-helper {
    margin-top: 4px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    line-height: 1.4;
  }
}

/* Reuse OPSflow card style locally */
.of-card {
  background: #f8f9fb;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  padding: 16px 18px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.of-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

/* Dialog styling */
:deep(.whitelist-dialog .el-dialog__header) {
  padding: 16px 20px;
  margin: 0;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
}
:deep(.whitelist-dialog .el-dialog__body) {
  padding: 20px;
}
:deep(.whitelist-dialog .el-dialog__footer) {
  padding: 12px 20px;
  border-top: 1px solid #e4e7ed;
}
</style>
