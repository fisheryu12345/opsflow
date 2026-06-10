<template>
  <div class="sys-page menu-page">
    <!-- ===== Stats Cards ===== -->
    <div class="menu-stats sys-fade-in-up">
      <div v-for="s in stats" :key="s.label" class="menu-stat-card">
        <div class="menu-stat-icon" :style="{ background: s.bg }">
          <el-icon :size="20"><component :is="s.icon" /></el-icon>
        </div>
        <div class="menu-stat-body">
          <div class="menu-stat-val">{{ s.value }}</div>
          <div class="menu-stat-lbl">{{ s.label }}</div>
        </div>
      </div>
    </div>

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

      <!-- ── Right: Tabs ── -->
      <el-col :span="18" class="menu-col">
        <div class="sys-card menu-tabs-card sys-fade-in-up" style="animation-delay:0.1s">
          <div class="menu-section-header">
            <el-icon :size="16"><Setting /></el-icon>
            <span>{{ $t('message.menuPage.permissionConfig') }}</span>
          </div>
          <el-tabs v-model="activeTab" class="menu-tabs">
            <el-tab-pane name="button">
              <template #label>
                <span class="menu-tab-label">
                  <el-icon :size="14"><Key /></el-icon>
                  <span>{{ $t('message.menuPage.btnPermission') }}</span>
                </span>
              </template>
              <div class="menu-tab-body">
                <MenuButtonCom ref="menuButtonRef" />
              </div>
            </el-tab-pane>
            <el-tab-pane name="field">
              <template #label>
                <span class="menu-tab-label">
                  <el-icon :size="14"><Grid /></el-icon>
                  <span>{{ $t('message.menuPage.colPermission') }}</span>
                </span>
              </template>
              <div class="menu-tab-body">
                <MenuFieldCom ref="menuFieldRef" />
              </div>
            </el-tab-pane>
          </el-tabs>
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
import { ref, computed, onMounted, markRaw } from 'vue';
import { useI18n } from 'vue-i18n';
import XEUtils from 'xe-utils';
import { ElMessageBox } from 'element-plus';
import { Search, Menu, Setting, Key, Grid, OfficeBuilding, Tickets, List } from '@element-plus/icons-vue';
import MenuTreeCom from './components/MenuTreeCom/index.vue';
import MenuButtonCom from './components/MenuButtonCom/index.vue';
import MenuFormCom from './components/MenuFormCom/index.vue';
import MenuFieldCom from './components/MenuFieldCom/index.vue';
import { GetList, DelObj } from './api';
import { successNotification } from '/@/utils/message';
import { APIResponseData, MenuTreeItemType } from './types';

const { t } = useI18n();

/* ===================== Stats ===================== */
const menuCount = ref(0);
const catalogCount = ref(0);
const leafCount = ref(0);
const stats = computed(() => [
  { label: t('message.menuPage.statTotal'), value: menuCount.value, icon: markRaw(OfficeBuilding), bg: 'linear-gradient(135deg,#409eff,#337ecc)' },
  { label: t('message.menuPage.statCatalog'), value: catalogCount.value, icon: markRaw(Tickets), bg: 'linear-gradient(135deg,#e6a23c,#f56c6c)' },
  { label: t('message.menuPage.statLeaf'), value: leafCount.value, icon: List, bg: 'linear-gradient(135deg,#67c23a,#409eff)' },
  { label: t('message.menuPage.statCurrent'), value: '---', icon: Search, bg: 'linear-gradient(135deg,#909399,#606266)' },
]);

/* ===================== State ===================== */
const menuTreeData = ref([]);
const menuTreeCacheData = ref<MenuTreeItemType[]>([]);
const drawerVisible = ref(false);
const drawerFormData = ref<Partial<MenuTreeItemType>>({});
const menuTreeRef = ref<InstanceType<typeof MenuTreeCom> | null>(null);
const menuButtonRef = ref<InstanceType<typeof MenuButtonCom> | null>(null);
const menuFieldRef = ref<InstanceType<typeof MenuFieldCom> | null>(null);
const activeTab = ref('button');

const countNodes = (arr: any[]) => {
  let cat = 0, leaf = 0;
  const walk = (nodes: any[]) => {
    for (const n of nodes) {
      if (n.is_catalog) cat++; else leaf++;
      if (n.children?.length) walk(n.children);
    }
  };
  walk(arr);
  catalogCount.value = cat;
  leafCount.value = leaf;
  menuCount.value = cat + leaf;
};

const getData = () => {
  GetList({}).then((ret: APIResponseData) => {
    const result = XEUtils.toArrayTree(ret.data, { parentKey: 'parent', children: 'children', strict: true });
    menuTreeData.value = result;
    countNodes(result);
  });
};

/* ===================== Handlers ===================== */
const handleTreeClick = (record: MenuTreeItemType) => {
  menuButtonRef.value?.handleRefreshTable(record);
  menuFieldRef.value?.handleRefreshTable(record);
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
  background: $g-gradient-hero;
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
