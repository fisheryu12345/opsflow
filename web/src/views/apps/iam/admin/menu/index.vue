<template>
  <div class="sys-page menu-page">
    <!-- ===== Main Content ===== -->
    <el-row class="menu-row" :gutter="14">
      <!-- ── Left: Menu Tree ── -->
      <el-col :span="6" class="menu-col">
        <div class="sys-card menu-tree-card sys-fade-in-up" style="animation-delay:0.06s">
          <div class="menu-section-header">
            <el-icon :size="16"><Menu /></el-icon>
            <span>{{ $t('message.menuPage.menuTree') }}</span>
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

      <!-- ── Right: Menu Detail Panel ── -->
      <el-col :span="18" class="menu-col">
        <div class="sys-card menu-tabs-card sys-fade-in-up" style="animation-delay:0.1s">
          <div class="menu-section-header">
            <el-icon :size="16"><Setting /></el-icon>
            <span>{{ selectedMenu ? selectedMenu.name : $t('message.menuPage.permissionConfig') }}</span>
          </div>
          <div class="menu-tab-body">
            <MenuDetailPanel
              :menu="selectedMenu"
              :treeData="menuTreeData"
              @edit="handleMenuEdit"
              @delete="handleMenuDeleteFromDetail"
              @refresh="getData"
            />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ===== Drawer: Menu Form ===== -->
    <el-drawer
      v-model="drawerVisible"
      :title="drawerFormData.id ? $t('message.menuPage.editMenu') : $t('message.menuPage.addMenu')"
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
import { useI18n } from 'vue-i18n';
import XEUtils from 'xe-utils';
import { ElMessageBox } from 'element-plus';
import { Menu, Setting, Key } from '@element-plus/icons-vue';
import MenuTreeCom from './components/MenuTreeCom/index.vue';
import MenuFormCom from './components/MenuFormCom/index.vue';
import MenuDetailPanel from './components/MenuDetailPanel/index.vue';
import { GetList, DelObj } from './api';
import { successNotification } from '/@/utils/message';
import { APIResponseData, MenuTreeItemType } from './types';

const { t } = useI18n();

/* ===================== State ===================== */
const menuTreeData = ref([]);
const menuTreeCacheData = ref<MenuTreeItemType[]>([]);
const drawerVisible = ref(false);
const drawerFormData = ref<Partial<MenuTreeItemType>>({});
const menuTreeRef = ref<InstanceType<typeof MenuTreeCom> | null>(null);
const selectedMenu = ref<MenuTreeItemType | null>(null);
// MenuButtonCom removed - button permission management moved to IAM role assignment

const getData = () => {
  const prevId = selectedMenu.value?.id;
  GetList({}).then((ret: APIResponseData) => {
    const result = XEUtils.toArrayTree(ret.data, { parentKey: 'parent', children: 'children', strict: true });
    menuTreeData.value = result;
    // Re-select previously selected menu after refresh
    if (prevId) {
      const flat = ret.data || [];
      const found = flat.find((i: any) => String(i.id) === String(prevId));
      if (found) selectedMenu.value = found;
    }
  });
};

/* ===================== Handlers ===================== */
const handleTreeClick = (record: MenuTreeItemType) => {
  selectedMenu.value = record;
};

const handleUpdateMenu = (type: string, record?: MenuTreeItemType) => {
  if (type === 'update' && record) {
    const parentData = menuTreeRef.value?.treeRef?.currentNode.parent.data || {};
    menuTreeCacheData.value = [parentData];
    drawerFormData.value = record;
  }
  drawerVisible.value = true;
};

const handleDrawerClose = (type?: string) => {
  if (type === 'submit') getData();
  else if (type === 'delete') getData();
  drawerVisible.value = false;
  drawerFormData.value = {};
};

const handleDeleteMenu = (id: string, callback: Function) => {
  ElMessageBox.confirm(t('message.menuPage.confirmDelete'), t('message.menuPage.confirm'), {
    confirmButtonText: t('message.menuPage.deleteBtn'),
    cancelButtonText: t('message.menuPage.cancelBtn'),
    type: 'warning',
  }).then(async () => {
    const res: APIResponseData = await DelObj(id);
    callback();
    if (res?.code === 2000) { successNotification(res.msg as string); getData(); }
  }).catch(() => {});
};

/* Detail panel event handlers */
const handleMenuEdit = (menu: MenuTreeItemType) => {
  handleUpdateMenu('update', menu);
};

const handleMenuDeleteFromDetail = (menu: MenuTreeItemType) => {
  handleDeleteMenu(String(menu.id), () => {
    selectedMenu.value = null;
  });
};

onMounted(() => { getData(); });
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.g-page {
  height: 100%;
  background: $g-bg-page;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ===== Stats ===== */
.menu-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
  padding: 12px 12px 0;
}
.menu-stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #fff;
  border-radius: $g-radius-card;
  padding: 16px 18px;
  box-shadow: $g-shadow-card;
}
.menu-stat-icon {
  width: 42px; height: 42px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  color: #fff;
}
.menu-stat-body { flex: 1; min-width: 0; }
.menu-stat-val { font-size: 22px; font-weight: 700; color: $g-text-primary; }
.menu-stat-lbl { font-size: 13px; color: $g-text-secondary; margin-top: 2px; }

/* ===== Layout ===== */
.menu-row {
  height: calc(100vh - 180px);
  overflow: hidden;
  margin: 0 12px !important;
}
.menu-col { height: 100%; }

.g-card {
  background: #fff;
  border: 1px solid $g-border-card;
  border-radius: $g-radius-card;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: $g-shadow-card;
}

/* ===== Section Header ===== */
.menu-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid $g-border-light;
  font-size: 14px;
  font-weight: 600;
  color: $g-text-primary;
  flex-shrink: 0;
}

/* ===== Tabs ===== */
.menu-tabs-card { display: flex; flex-direction: column; overflow: hidden; }
.menu-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.menu-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 8px 16px 0;
  border-bottom: 1px solid $g-border-light;
}
.menu-tab-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.menu-tab-body {
  height: 100%;
  overflow: auto;
  padding: 12px 16px;
}
</style>
