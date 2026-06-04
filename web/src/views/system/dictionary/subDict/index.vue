<template>
  <!-- 子字典抽屉 / Sub-dictionary drawer -->
  <el-drawer
    v-model="drawerVisible"
    size="70%"
    direction="rtl"
    destroy-on-close
    title="字典配置"
    :before-close="handleClose"
  >
    <!-- 搜索栏 / Search bar -->
    <div class="subdict-search">
      <el-form :model="searchForm" inline>
        <el-form-item label="名称">
          <el-input v-model="searchForm.label" placeholder="请输入名称" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 工具栏 / Toolbar -->
    <div class="subdict-toolbar">
      <el-button type="primary" icon="Plus" @click="openAddDialog">新增</el-button>
    </div>

    <!-- 数据表格 / Data table -->
    <el-table
      :data="tableData"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
      size="small"
    >
      <el-table-column type="index" label="序号" width="70" align="center">
        <template #default="{ $index }">
          {{ ((pagination.currentPage - 1) * pagination.pageSize) + $index + 1 }}
        </template>
      </el-table-column>
      <el-table-column prop="label" label="名称" min-width="120" show-overflow-tooltip />
      <el-table-column prop="value" label="数据值" min-width="120" show-overflow-tooltip />
      <el-table-column prop="type" label="数据值类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small">{{ typeMap[row.type] || row.type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.status"
            @change="(val: boolean) => handleStatusChange(row, val)"
            inline-prompt
            active-text=""
            inactive-text=""
            style="--el-switch-on-color: var(--el-color-primary); --el-switch-off-color: #dcdfe6"
          />
        </template>
      </el-table-column>
      <el-table-column prop="sort" label="排序" width="70" align="center" />
      <el-table-column prop="color" label="标签颜色" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.color" :type="row.color" effect="plain" size="small">
            {{ row.color }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openEditDialog(row)">
            编辑
          </el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 / Pagination -->
    <div class="subdict-pagination">
      <el-pagination
        v-model:current-page="pagination.currentPage"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="getList"
        @size-change="getList"
      />
    </div>
  </el-drawer>

  <!-- 新增/编辑弹窗 / Add/Edit dialog -->
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑字典项' : '新增字典项'"
    width="500px"
    append-to-body
    destroy-on-close
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="100px"
      label-position="right"
      size="small"
    >
      <el-form-item label="名称" prop="label">
        <el-input v-model="formData.label" placeholder="请输入名称" clearable />
      </el-form-item>
      <el-form-item label="数据值" prop="value">
        <el-input v-model="formData.value" placeholder="请输入数据值" clearable />
      </el-form-item>
      <el-form-item label="数据值类型" prop="type">
        <el-select v-model="formData.type" placeholder="请选择数据值类型" style="width: 100%">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="formData.status">
          <el-radio :value="true">启用</el-radio>
          <el-radio :value="false">禁用</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="排序" prop="sort">
        <el-input-number v-model="formData.sort" :min="0" />
      </el-form-item>
      <el-form-item label="标签颜色" prop="color">
        <el-select v-model="formData.color" placeholder="请选择标签颜色" clearable style="width: 100%">
          <el-option
            v-for="item in colorOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          >
            <el-tag :type="item.value" size="small">{{ item.label }}</el-tag>
          </el-option>
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import type { FormInstance } from 'element-plus';
import { ElMessageBox } from 'element-plus';
import { successMessage } from '/@/utils/message';
import * as api from './api';
import type { DictItem } from './api';

/* ---------- 数据值类型映射 / Type display map ---------- */
const typeMap: Record<number, string> = {
  0: 'text',
  1: 'number',
  2: 'date',
  3: 'datetime',
  4: 'time',
  5: 'file',
  6: 'boolean',
  7: 'images',
};

const typeOptions = Object.entries(typeMap).map(([value, label]) => ({
  value: Number(value),
  label,
}));

/* ---------- 标签颜色选项 / Color select options ---------- */
const colorOptions = [
  { label: 'success', value: 'success' as const },
  { label: 'primary', value: 'primary' as const },
  { label: 'info', value: 'info' as const },
  { label: 'danger', value: 'danger' as const },
  { label: 'warning', value: 'warning' as const },
];

/* ---------- 抽屉状态 / Drawer state ---------- */
const drawerVisible = ref(false);

/* ---------- 父字典 ID（由外部传入） / Parent dict ID ---------- */
const parentId = ref<number | null>(null);

/* ---------- 搜索表单 / Search form ---------- */
const searchForm = reactive({
  label: '',
});

/* ---------- 表格数据 / Table data ---------- */
const tableData = ref<DictItem[]>([]);
const loading = ref(false);
const pagination = reactive({
  currentPage: 1,
  pageSize: 15,
  total: 0,
});

/* ---------- 表单弹窗 / Form dialog ---------- */
const dialogVisible = ref(false);
const isEdit = ref(false);
const submitLoading = ref(false);
const formRef = ref<FormInstance>();
const formData = reactive<DictItem>({
  label: '',
  value: '',
  type: 0,
  status: true,
  sort: 1,
  color: '',
});

/* 表单校验规则 / Form validation rules */
const formRules = {
  label: [{ required: true, message: '名称必填项', trigger: 'blur' }],
  value: [{ required: true, message: '数据值必填项', trigger: 'blur' }],
  type: [{ required: true, message: '数据值类型必填项', trigger: 'change' }],
  status: [{ required: true, message: '状态必填项', trigger: 'change' }],
  sort: [{ required: true, message: '排序必填项', trigger: 'blur' }],
};

/* ---------- 获取列表数据 / Fetch list data ---------- */
async function getList() {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: pagination.currentPage,
      limit: pagination.pageSize,
    };
    if (searchForm.label) {
      params.label = searchForm.label;
    }
    if (parentId.value) {
      params.parent = parentId.value;
    }
    const res: any = await api.GetList(params);
    tableData.value = res.data || [];
    pagination.total = res.total || 0;
  } finally {
    loading.value = false;
  }
}

/* ---------- 搜索 / Search ---------- */
function handleSearch() {
  pagination.currentPage = 1;
  getList();
}

/* ---------- 重置搜索 / Reset search ---------- */
function handleReset() {
  searchForm.label = '';
  pagination.currentPage = 1;
  getList();
}

/* ---------- 表格内状态切换 / Inline status toggle ---------- */
function handleStatusChange(row: DictItem, val: boolean) {
  api.UpdateObj({ id: row.id, status: val }).then((res: any) => {
    successMessage(res.msg || '更新成功');
    row.status = val;
  });
}

/* ---------- 打开新增弹窗 / Open add dialog ---------- */
function openAddDialog() {
  isEdit.value = false;
  formData.label = '';
  formData.value = '';
  formData.type = 0;
  formData.status = true;
  formData.sort = 1;
  formData.color = '';
  dialogVisible.value = true;
}

/* ---------- 打开编辑弹窗 / Open edit dialog ---------- */
function openEditDialog(row: DictItem) {
  isEdit.value = true;
  formData.id = row.id;
  formData.label = row.label;
  formData.value = row.value;
  formData.type = row.type;
  formData.status = row.status;
  formData.sort = row.sort;
  formData.color = row.color || '';
  dialogVisible.value = true;
}

/* ---------- 提交表单 / Submit form ---------- */
async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitLoading.value = true;
  try {
    const data = { ...formData };
    if (parentId.value) {
      (data as any).parent = parentId.value;
    }
    const res: any = isEdit.value
      ? await api.UpdateObj(data)
      : await api.AddObj(data);
    successMessage(res.msg || (isEdit.value ? '更新成功' : '新增成功'));
    dialogVisible.value = false;
    getList();
  } finally {
    submitLoading.value = false;
  }
}

/* ---------- 删除字典项 / Delete item ---------- */
function handleDelete(row: DictItem) {
  ElMessageBox.confirm('确定删除该字典项吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    api.DelObj(row.id!).then((res: any) => {
      successMessage(res.msg || '删除成功');
      getList();
    });
  }).catch(() => {
    /* 取消删除不做任何操作 */
  });
}

/* ---------- 关闭抽屉确认 / Confirm drawer close ---------- */
function handleClose(done: () => void) {
  ElMessageBox.confirm('您确定要关闭?', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      done();
    })
    .catch(() => {
      /* 取消关闭 */
    });
}

/* ---------- 外部接口 / Public API ---------- */
/*
 * 设置搜索表单数据（由父组件调用，传入父字典 ID）
 * Set search form data, called by parent with parent dict row.id
 */
function setSearchFormData(data: { form?: { parent?: number } }) {
  if (data?.form?.parent) {
    parentId.value = data.form.parent;
  }
}

/*
 * 强制刷新列表（由父组件调用）
 * Force refresh list, called by parent
 */
function doRefresh() {
  pagination.currentPage = 1;
  getList();
}

/* 暴露给父组件的属性和方法 / Expose to parent component */
defineExpose({
  drawer: drawerVisible,
  setSearchFormData,
  doRefresh,
});
</script>

<style lang="scss" scoped>
.subdict-search {
  padding-bottom: 16px;
}

.subdict-toolbar {
  padding-bottom: 16px;
}

.subdict-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}
</style>
