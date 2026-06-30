<template>
  <el-drawer
    v-model="drawerVisible"
    title="权限配置"
    direction="rtl"
    size="60%"
    :close-on-click-modal="false"
    :before-close="handleDrawerClose"
    :destroy-on-close="true"
    class="pc-drawer"
  >
    <template #header>
      <div class="pc-drawer-header">
        <div class="pc-drawer-title">
          <span class="pc-drawer-icon">
            <el-icon :size="16"><Setting /></el-icon>
          </span>
          <span>权限配置</span>
        </div>
        <div class="pc-drawer-meta">
          <span class="pc-role-label">当前角色：</span>
          <el-tag type="primary" effect="dark" round>{{ props.roleName }}</el-tag>
        </div>
        <el-button type="primary" size="small" :icon="Plus" @click="handleSavePermission" class="pc-save-btn">
          保存菜单授权
        </el-button>
      </div>
    </template>

    <div class="pc-body" v-loading="loading">
      <!-- 空状态 -->
      <el-empty v-if="!loading && menuData.length === 0" :image-size="60" description="暂无权限数据" />

      <!-- 菜单权限列表 -->
      <el-collapse v-if="menuData.length > 0" v-model="collapseCurrent" @change="handleCollapseChange" accordion>
        <el-collapse-item v-for="(item, mIndex) in menuData" :key="mIndex" :name="mIndex">
          <template #title>
            <div class="pc-collapse-title-wrap">
              <div class="pc-collapse-title">
                <el-checkbox v-model="item.isCheck" @click.stop>
                  <span class="pc-menu-name">{{ item.name }}</span>
                </el-checkbox>
              </div>
              <div v-if="!collapseCurrent.includes(mIndex)" class="pc-collapse-btns" @click.stop>
                <el-checkbox v-for="btn in item.btns" :key="btn.value" v-model="btn.isCheck" :label="btn.value" size="small">
                  {{ btn.name }}
                </el-checkbox>
              </div>
            </div>
          </template>

          <div class="pc-collapse-body">
            <!-- 按钮权限 -->
            <div class="pc-section">
              <div class="pc-section-label">
                <el-icon><Operation /></el-icon> 操作权限
              </div>
              <div class="pc-btn-grid">
                <div v-for="(btn, bIndex) in item.btns" :key="bIndex" class="pc-btn-card" :class="{ 'is-checked': btn.isCheck }">
                  <el-checkbox v-model="btn.isCheck" :label="btn.value">
                    <div class="pc-btn-info">
                      <span class="pc-btn-name">
                        {{ btn.name }}
                        <span v-if="btn.data_range !== null" class="pc-btn-range">
                          ({{ formatDataRange(btn.data_range) }})
                        </span>
                      </span>
                    </div>
                  </el-checkbox>
                  <el-button
                    v-if="btn.isCheck"
                    text
                    type="primary"
                    size="small"
                    class="pc-btn-setting"
                    @click.stop="handleSettingClick(item, btn.id)"
                  >
                    <el-icon><Setting /></el-icon> 数据范围
                  </el-button>
                </div>
              </div>
            </div>

            <!-- 字段权限 -->
            <div class="pc-section">
              <div class="pc-section-label">
                <el-icon><List /></el-icon> 字段权限
              </div>
              <div class="pc-columns-table-wrap">
                <table class="pc-columns-table">
                  <thead>
                    <tr>
                      <th class="pc-col-field">字段</th>
                      <th v-for="(head, hIndex) in column.header" :key="hIndex" class="pc-col-check">
                        <el-checkbox :label="head.value" @change="(val: any) => handleColumnChange(val, item, head.value)">
                          {{ head.label }}
                        </el-checkbox>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(c_item, c_index) in item.columns" :key="c_index">
                      <td class="pc-col-field">{{ c_item.title }}</td>
                      <td v-for="(col, cIndex) in column.header" :key="cIndex" class="pc-col-check">
                        <el-checkbox v-model="c_item[col.value]" />
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>

      <!-- 数据权限 Dialog -->
      <el-dialog
        v-model="dialogVisible"
        title="数据权限配置"
        width="420px"
        :close-on-click-modal="false"
        :before-close="handleDialogClose"
        class="opsflow-dialog"
        append-to-body
      >
        <div class="pc-dialog-body">
          <el-select v-model="dataPermission" @change="handlePermissionRangeChange" class="pc-dialog-select" placeholder="请选择数据范围">
            <el-option v-for="item in dataPermissionRange" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-tree-select
            v-if="dataPermission === 4"
            v-model="customDataPermission"
            :props="defaultTreeProps"
            :data="deptData"
            node-key="id"
            multiple
            check-strictly
            :render-after-expand="false"
            show-checkbox
            class="pc-dialog-tree"
            placeholder="选择自定义部门"
          />
        </div>
        <template #footer>
          <el-button @click="handleDialogClose">取消</el-button>
          <el-button type="primary" round @click="handleDialogConfirm">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, reactive, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { Setting, Plus, Operation, List } from '@element-plus/icons-vue';
import XEUtils from 'xe-utils';
import { errorNotification } from '/@/utils/message';
import {
  getDataPermissionRange, getDataPermissionDept,
  getRolePremission, setRolePremission,
} from './api';
import { MenuDataType, DataPermissionRangeType, CustomDataPermissionDeptType } from './types';

const props = defineProps({
  roleId: { type: Number, default: -1 },
  roleName: { type: String, default: '' },
  drawerVisible: { type: Boolean, default: false },
});
const emit = defineEmits(['update:drawerVisible']);

const drawerVisible = ref(false);
watch(() => props.drawerVisible, (val) => {
  drawerVisible.value = val;
  if (val) {
    getMenuBtnPermission();
    fetchData();
  }
});

const handleDrawerClose = () => emit('update:drawerVisible', false);

const defaultTreeProps = { children: 'children', label: 'name', value: 'id' };

const loading = ref(false);
const menuData = ref<MenuDataType[]>([]);
const collapseCurrent = ref<string[]>([]);
const menuCurrent = ref<Partial<MenuDataType>>({});
const menuBtnCurrent = ref<number>(-1);
const dialogVisible = ref(false);
const dataPermissionRange = ref<DataPermissionRangeType[]>([]);

const formatDataRange = computed(() => {
  return (datarange: number) => {
    const found = dataPermissionRange.value.find(i => i.value === datarange);
    return found?.label || '';
  };
});

const deptData = ref<CustomDataPermissionDeptType[]>([]);
const dataPermission = ref<number | null>(null);
const customDataPermission = ref<any[]>([]);

const getMenuBtnPermission = async () => {
  loading.value = true;
  try {
    const res = await getRolePremission({ role: props.roleId });
    if (res?.code === 2000) {
      menuData.value = res.data || [];
    } else {
      menuData.value = [];
    }
  } catch (e) {
    console.error('获取权限配置异常:', e);
    menuData.value = [];
  } finally {
    loading.value = false;
  }
};

const fetchData = async () => {
  try {
    const res = await getDataPermissionRange();
    if (res?.code === 2000) {
      dataPermissionRange.value = res.data;
    }
  } catch { /* noop */ }
};

const handleCollapseChange = (val: string | string[]) => {
  collapseCurrent.value = Array.isArray(val) ? val : [val];
};

const handleSettingClick = (record: MenuDataType, btnId: number) => {
  menuCurrent.value = record;
  menuBtnCurrent.value = btnId;
  dialogVisible.value = true;
};

const handleColumnChange = (val: boolean, record: MenuDataType, field: string) => {
  for (const col of record.columns) {
    col[field] = val;
  }
};

const handlePermissionRangeChange = async (val: number) => {
  if (val === 4) {
    const res = await getDataPermissionDept();
    const data = XEUtils.toArrayTree(res.data, { parentKey: 'parent', strict: false });
    deptData.value = data;
  }
};

const handleDialogConfirm = () => {
  if (dataPermission.value !== 0 && !dataPermission.value) {
    errorNotification('请选择数据范围');
    return;
  }
  for (const menu of menuData.value) {
    if (menu.id === menuCurrent.value.id) {
      for (const btn of menu.btns) {
        if (btn.id === menuBtnCurrent.value) {
          const found = dataPermissionRange.value.find(i => i.value === dataPermission.value);
          btn.data_range = found?.value || 0;
          if (btn.data_range === 4) {
            btn.dept = customDataPermission.value as any;
          }
        }
      }
    }
  }
  handleDialogClose();
};

const handleDialogClose = () => {
  dialogVisible.value = false;
  customDataPermission.value = [];
  dataPermission.value = null;
};

const handleSavePermission = async () => {
  try {
    const res = await setRolePremission(props.roleId, menuData.value);
    if (res?.code === 2000) {
      ElMessage.success(res.msg || '权限保存成功');
    } else {
      ElMessage.error(res?.msg || '保存失败');
    }
  } catch (e: any) {
    ElMessage.error(e?.msg || '保存失败');
  }
};

const column = reactive({
  header: [
    { value: 'is_create', label: '新增可见' },
    { value: 'is_update', label: '编辑可见' },
    { value: 'is_query', label: '列表可见' },
  ],
});
</script>

<style scoped lang="scss">
// Design tokens (inline to avoid dependency issues)
$g-color-primary: #409eff;
$g-bg-light-blue: #ecf5ff;
$g-bg-card-hover: #f5f9ff;
$g-bg-header: #f5f7fa;
$g-bg-card: #f8f9fb;
$g-text-primary: #303133;
$g-text-secondary: #666;
$g-text-muted: #909399;
$g-border-light: #ebeef5;
$g-border-card: #f0f0f0;
$g-radius-sm: 8px;
$g-radius-card: 10px;
$g-shadow-card: 0 1px 4px rgba(0,0,0,.06);
$g-transition-default: .2s;

/* ===== Drawer ===== */
.pc-drawer {
  :deep(.el-drawer__header) {
    margin-bottom: 0;
    padding: 0;
  }
  :deep(.el-drawer__body) {
    padding: 0;
  }
}

.pc-drawer-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  width: 100%;
  padding: 0 4px;
}

.pc-drawer-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: $g-text-primary;
}

.pc-drawer-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.pc-drawer-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: $g-text-muted;
  margin-left: 4px;

  .pc-role-label {
    white-space: nowrap;
  }
}

.pc-save-btn {
  margin-left: auto;
}

/* ===== Body ===== */
.pc-body {
  padding: 16px 20px;
  min-height: 200px;
}

/* ===== Collapse Item ===== */
.pc-collapse-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  padding: 2px 0;
}

.pc-collapse-title {
  .pc-menu-name {
    font-size: 15px;
    font-weight: 600;
    color: $g-text-primary;
  }
}

.pc-collapse-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;

  :deep(.el-checkbox) {
    margin-right: 0;
    .el-checkbox__label {
      font-size: 12px;
      color: $g-text-muted;
    }
  }
}

/* ===== Collapse Body Sections ===== */
.pc-collapse-body {
  padding: 6px 0;
}

.pc-section {
  margin-bottom: 20px;

  &:last-child {
    margin-bottom: 0;
  }
}

.pc-section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: $g-text-secondary;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid $g-border-card;

  .el-icon {
    font-size: 14px;
    color: $g-color-primary;
  }
}

/* ===== Button Permission Cards ===== */
.pc-btn-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pc-btn-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid $g-border-card;
  border-radius: $g-radius-sm;
  background: #fafbfc;
  transition: border-color $g-transition-default, background $g-transition-default;

  &:hover {
    border-color: $g-color-primary;
    background: $g-bg-light-blue;
  }

  &.is-checked {
    border-color: $g-color-primary;
    background: $g-bg-light-blue;
  }

  :deep(.el-checkbox) {
    margin-right: 0;
    height: auto;
    .el-checkbox__label {
      font-size: 13px;
    }
  }
}

.pc-btn-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.pc-btn-name {
  font-size: 13px;
  color: $g-text-primary;
  line-height: 1.4;
}

.pc-btn-range {
  font-size: 11px;
  color: $g-text-muted;
  font-weight: 400;
}

.pc-btn-setting {
  flex-shrink: 0;
}

/* ===== Columns Table ===== */
.pc-columns-table-wrap {
  overflow-x: auto;
}

.pc-columns-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  thead tr {
    background: $g-bg-header;
  }

  th, td {
    padding: 8px 12px;
    border: 1px solid $g-border-light;
    text-align: center;
    white-space: nowrap;
  }

  .pc-col-field {
    width: 160px;
    text-align: left;
    font-weight: 500;
    color: $g-text-primary;
  }

  .pc-col-check {
    width: 100px;
    text-align: center;
  }

  thead .pc-col-field {
    font-weight: 600;
  }

  tbody tr {
    transition: background $g-transition-default;
    &:hover {
      background: $g-bg-card-hover;
    }
  }
}

/* ===== Data Range Dialog ===== */
.pc-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pc-dialog-select {
  width: 100%;
}

.pc-dialog-tree {
  width: 100%;
}
</style>

<style lang="scss">
/* Unscoped global overrides for el-collapse */
$g-border-light: #ebeef5;
$g-bg-card: #f8f9fb;
$g-color-primary: #409eff;
$g-radius-sm: 8px;

.pc-body {
  .el-collapse {
    border-top: none;
    border-bottom: none;
  }

  .el-collapse-item {
    margin-bottom: 12px;
    border: 1px solid $g-border-light;
    border-radius: $g-radius-sm;
    overflow: hidden;
    transition: box-shadow 0.2s;

    &:hover {
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
  }

  .el-collapse-item__header {
    height: auto;
    padding: 12px 16px;
    background: #fafbfc;
    border-bottom: 1px solid $g-border-light;
    font-weight: 500;
  }

  .el-collapse-item__header.is-active {
    background: linear-gradient(135deg, #ecf5ff 0%, #f8f9fb 100%);
  }

  .el-collapse-item__wrap {
    padding: 14px 16px;
    background: #fff;
  }

  .el-collapse-item__content {
    padding-bottom: 0;
  }
}
</style>
