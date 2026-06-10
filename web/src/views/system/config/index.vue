<template>
  <div class="sys-page">
    <!-- Main Card / 主卡片 -->
    <div class="sys-card g-fade-in-up">
      <!-- Card Header / 卡片头部 -->
      <div class="sys-card-header">
        <div class="sys-card-title">
          <span class="sys-card-icon">
            <el-icon :size="16"><Setting /></el-icon>
          </span>
          <span>{{ $t('message.menuPage.configTitle') }}</span>
          <el-tag size="small" type="info" effect="plain" class="g-tag-subtitle">
            {{ $t('message.menuPage.configSubtitle') }}
          </el-tag>
        </div>
        <div class="g-card-extra">
          <el-button type="primary" size="small" :icon="FolderAdd" @click="tabsDrawer = true">{{ $t('message.menuPage.configAddGroup') }}</el-button>
          <el-button size="small" type="warning" :icon="Edit" @click="contentDrawer = true">{{ $t('message.menuPage.configAddContent') }}</el-button>
        </div>
      </div>

      <!-- Card Body: Config Tabs / 配置选项卡 -->
      <el-tabs type="border-card" v-model="editableTabsValue" class="config-tabs">
        <el-tab-pane
          v-for="(item, index) in editableTabs"
          :key="index"
          :label="item.title"
          :name="item.key"
        >
          <template v-if="item.icon" #label>
            <i :class="item.icon" style="font-weight: 1000; font-size: 16px"></i>
          </template>
          <el-row v-if="item.icon">
            <el-col :offset="4" :span="8">
              <addContent></addContent>
            </el-col>
          </el-row>
          <formContent v-else :options="item" :editableTabsItem="item"></formContent>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- Add Group Drawer / 添加分组抽屉 -->
    <el-drawer v-if="tabsDrawer" :title="$t('message.menuPage.configAddGroupTitle')" v-model="tabsDrawer" direction="rtl" size="30%">
      <addTabs></addTabs>
    </el-drawer>

    <!-- Add Content Drawer / 添加内容抽屉 -->
    <el-drawer v-if="contentDrawer" :title="$t('message.menuPage.configAddContentTitle')" v-model="contentDrawer" direction="rtl" size="30%">
      <addContent></addContent>
    </el-drawer>
  </div>
</template>

<script lang="ts" setup name="config">
import { Edit, FolderAdd, Setting } from '@element-plus/icons-vue';
import * as api from './api';
import addTabs from './components/addTabs.vue';
import addContent from './components/addContent.vue';
import formContent from './components/formContent.vue';
import { ref, onMounted } from 'vue';

let tabsDrawer = ref(false);
let contentDrawer = ref(false);
let editableTabsValue = ref('base');
let editableTabs: any = ref([]);

const getTabs = () => {
  api
    .GetList({
      limit: 999,
      parent__isnull: true,
    })
    .then((res: any) => {
      let data = res.data;
      data.push({
        title: '无',
        icon: 'el-icon-plus',
        key: 'null',
      });
      editableTabs.value = data;
    });
};

onMounted(() => {
  getTabs();
});
</script>

<style scoped lang="scss">
@use '/@/styles/global' as *;

// ============================================================
// Animations / 动画 (g-fade-in-up for OPSflow consistency)
// ============================================================
.g-fade-in-up {
  animation: gFadeInUp 0.5s ease both;
}
@keyframes gFadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

// ============================================================
// Config Tab Override / 配置选项卡样式覆盖
// Seamlessly integrates border-card tabs into sys-card
// ============================================================
.config-tabs {
  :deep(.el-tabs--border-card) {
    border: none;
    border-radius: 0;
    box-shadow: none;
  }

  :deep(.el-tabs--border-card > .el-tabs__header) {
    background-color: #fafbfc;
    border-bottom: 1px solid $g-border-light;
    padding: 0 20px;
    margin: 0;
  }

  :deep(.el-tabs--border-card > .el-tabs__header .el-tabs__item) {
    height: 40px;
    line-height: 40px;
    transition: color 0.2s;

    &.is-active {
      color: $g-color-primary;
      font-weight: 600;
    }

    &:hover {
      color: $g-color-primary;
    }
  }

  :deep(.el-tabs--border-card > .el-tabs__body) {
    padding: 20px;
  }
}

// ============================================================
// Subtitle Tag / 副标题标签
// ============================================================
.g-tag-subtitle {
  font-size: 11px;
  border: none;
  background: transparent;
  color: $g-text-secondary !important;
}
</style>
