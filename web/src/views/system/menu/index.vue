<template>
  <div class="sys-page menu-page">
    <!-- ===== Section: Menu Tree + Tabs ===== -->
    <div class="menu-body">
      <el-row class="menu-row" :gutter="16">
        <!-- ── Left: Menu Tree ── -->
        <el-col :span="6" class="menu-col-left">
          <div class="sys-card menu-tree-card of-fade-in-up">
            <div class="menu-section-header">
              <div class="menu-header-icon">
                <el-icon :size="16"><Menu /></el-icon>
              </div>
              <span>Menu Tree / 菜单树</span>
            </div>
            <MenuTreeCom
              ref="menuTreeRef"
              :treeData="menuTreeData"
              @treeClick="handleTreeClick"
              @updateDept="handleUpdateMenu"
              @deleteDept="handleDeleteMenu"
            />
          </div>
        </el-col>

        <!-- ── Right: Tabs ── -->
        <el-col :span="18" class="menu-col-right">
          <div class="sys-card menu-tabs-card of-fade-in-up" :style="{ animationDelay: '0.1s' }">
            <div class="menu-section-header">
              <div class="menu-header-icon menu-header-icon-accent">
                <el-icon :size="16"><Setting /></el-icon>
              </div>
              <span>Permission Config / 权限配置</span>
            </div>
            <el-tabs v-model="activeTab" type="border-card" class="menu-tabs">
              <el-tab-pane label="Button Permissions / 按钮权限配置" name="button">
                <div class="menu-tab-content">
                  <MenuButtonCom ref="menuButtonRef" />
                </div>
              </el-tab-pane>
              <el-tab-pane label="Column Permissions / 列权限配置" name="field">
                <div class="menu-tab-content">
                  <MenuFieldCom ref="menuFieldRef" />
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- ===== Drawer: Menu Form ===== -->
    <el-drawer
      v-model="drawerVisible"
      title="Menu Config / 菜单配置"
      direction="rtl"
      size="540px"
      :close-on-click-modal="false"
      :before-close="handleDrawerClose"
      class="opsflow-drawer"
    >
      <MenuFormCom
        v-if="drawerVisible"
        :initFormData="drawerFormData"
        :cacheData="menuTreeCacheData"
        :treeData="menuTreeData"
        @drawerClose="handleDrawerClose"
      />
    </el-drawer>
  </div>
</template>

<script lang="ts" setup name="menuPages">
import { ref, onMounted } from 'vue';
import XEUtils from 'xe-utils';
import { ElMessageBox } from 'element-plus';
import { Menu, Setting } from '@element-plus/icons-vue';
import MenuTreeCom from './components/MenuTreeCom/index.vue';
import MenuButtonCom from './components/MenuButtonCom/index.vue';
import MenuFormCom from './components/MenuFormCom/index.vue';
import MenuFieldCom from './components/MenuFieldCom/index.vue';
import { GetList, DelObj } from './api';
import { successNotification } from '/@/utils/message';
import { APIResponseData, MenuTreeItemType } from './types';

let menuTreeData = ref([]);
let menuTreeCacheData = ref<MenuTreeItemType[]>([]);
let drawerVisible = ref(false);
let drawerFormData = ref<Partial<MenuTreeItemType>>({});
let menuTreeRef = ref<InstanceType<typeof MenuTreeCom> | null>(null);
let menuButtonRef = ref<InstanceType<typeof MenuButtonCom> | null>(null);
let menuFieldRef = ref<InstanceType<typeof MenuFieldCom> | null>(null);
let activeTab = ref('button');

const getData = () => {
  GetList({}).then((ret: APIResponseData) => {
    const responseData = ret.data;
    const result = XEUtils.toArrayTree(responseData, {
      parentKey: 'parent',
      children: 'children',
      strict: true,
    });
    menuTreeData.value = result;
  });
};

/**
 * Menu click event / 菜单的点击事件
 */
const handleTreeClick = (record: MenuTreeItemType) => {
  menuButtonRef.value?.handleRefreshTable(record);
  menuFieldRef.value?.handleRefreshTable(record);
};

/**
 * Menu add/edit event / 菜单的新增或编辑事件
 */
const handleUpdateMenu = (type: string, record?: MenuTreeItemType) => {
  if (type === 'update' && record) {
    const parentData = menuTreeRef.value?.treeRef?.currentNode.parent.data || {};
    menuTreeCacheData.value = [parentData];
    drawerFormData.value = record;
  }
  drawerVisible.value = true;
};

const handleDrawerClose = (type?: string) => {
  if (type === 'submit') {
    getData();
  }
  drawerVisible.value = false;
  drawerFormData.value = {};
};

/**
 * Menu delete event / 菜单的删除事件
 */
const handleDeleteMenu = (id: string, callback: Function) => {
  ElMessageBox.confirm('Are you sure you want to delete this menu item? / 您确认删除该菜单项吗?', 'Confirm / 温馨提示', {
    confirmButtonText: 'Confirm / 确认',
    cancelButtonText: 'Cancel / 取消',
    type: 'warning',
  }).then(async () => {
    const res: APIResponseData = await DelObj(id);
    callback();
    if (res?.code === 2000) {
      successNotification(res.msg as string);
      getData();
    }
  });
};

onMounted(() => {
  getData();
});
</script>

<style lang="scss" scoped>
@import '../../apps/opsflow/styles/opsflow-global';

.sys-page {
  height: 100%;
  background: $of-bg-page;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.menu-body {
  flex: 1;
  overflow: hidden;
  padding: 12px;
}

.menu-row {
  height: 100%;
  overflow: hidden;

  .el-col {
    height: 100%;
    overflow: hidden;
  }
}

.menu-col-left,
.menu-col-right {
  padding-bottom: 0;
}

.sys-card {
  background: #fff;
  border: 1px solid $of-border-card;
  border-radius: $of-radius-card;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: $of-shadow-card;
  transition: box-shadow $of-transition-default;
}

.sys-card:hover {
  box-shadow: $of-shadow-hover;
}

/* ===== Section Header ===== */
.menu-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: $of-gradient-hero;
  border-bottom: 1px solid $of-border-light;
  font-size: 14px;
  font-weight: 600;
  color: $of-text-primary;
  flex-shrink: 0;
}

.menu-header-icon {
  @include of-icon-circle(30px, $of-gradient-blue);
}

.menu-header-icon-accent {
  background: $of-gradient-accent;
}

/* ===== Tabs Card ===== */
.menu-tabs-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.menu-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: none !important;
  background: transparent !important;
}

.menu-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 8px 16px 0;
  background: transparent;
  border-bottom: 1px solid $of-border-light;
}

.menu-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0;
}

.menu-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  padding: 0 16px;
  height: 36px;
  line-height: 36px;
  transition: color $of-transition-default;
}

.menu-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
  color: $of-color-primary;
}

.menu-tabs :deep(.el-tabs__active-bar) {
  height: 2px;
  background: $of-gradient-blue;
}

.menu-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.menu-tabs :deep(.el-tab-pane) {
  height: 100%;
  overflow: hidden;
}

.menu-tab-content {
  height: 100%;
  overflow: auto;
  padding: 12px 16px;
}

/* ===== Tree Card ===== */
.menu-tree-card {
  overflow: hidden;
}

/* ===== Drawer ===== */
.opsflow-drawer :deep(.el-drawer__header) {
  @include of-dialog-header;
  background: $of-gradient-blue;
  color: #fff;
  margin-bottom: 0;
}

.opsflow-drawer :deep(.el-drawer__title) {
  color: #fff;
  font-size: 15px;
}

.opsflow-drawer :deep(.el-drawer__close-btn) {
  color: rgba(255, 255, 255, 0.8);
  font-size: 18px;
}

.opsflow-drawer :deep(.el-drawer__close-btn:hover) {
  color: #fff;
}

.opsflow-drawer :deep(.el-drawer__body) {
  @include of-dialog-body;
  overflow-y: auto;
}

.opsflow-drawer :deep(.el-drawer__footer) {
  @include of-dialog-footer;
}
</style>
