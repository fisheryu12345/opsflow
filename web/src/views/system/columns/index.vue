<template>
  <div class="sys-page columns-page">
    <!-- ===== Section Header ===== -->
    <div class="columns-header of-fade-in-up">
      <div class="columns-header-bg" />
      <div class="columns-header-inner">
        <div class="columns-header-icon">
          <el-icon :size="18"><List /></el-icon>
        </div>
        <div class="columns-header-text">
          <div class="columns-header-title">列权限管理</div>
          <div class="columns-header-desc">配置角色对模型字段的创建、编辑、查询权限</div>
        </div>
      </div>
    </div>

    <!-- ===== 3-Column Layout ===== -->
    <div class="columns-body">
      <el-row :gutter="10" class="columns-row">
        <el-col :span="6" class="of-fade-in-up" style="animation-delay: 0.05s">
          <div class="sys-card">
            <ItemCom title="角色" type="role" showPagination @fetchData="fetchRoleData" @itemClick="handleClick" />
          </div>
        </el-col>
        <!--<el-col :span="4" class="of-fade-in-up" style="animation-delay: 0.07s">
          <div class="sys-card">
            <ItemCom title="菜单" type="menu" showPagination @fetchData="fetchMenuData" @itemClick="handleClick" />
          </div>
        </el-col>-->
        <el-col :span="8" class="of-fade-in-up" style="animation-delay: 0.10s">
          <div class="sys-card">
            <ItemCom title="模型表" type="model" label="showText" value="key" @fetchData="fetchModelData" @itemClick="handleClick" />
          </div>
        </el-col>
        <el-col :span="10" class="of-fade-in-up" style="animation-delay: 0.15s">
          <div class="sys-card">
            <ColumnsTableCom ref="columnsTableRef" :currentInfo="currentInfo" />
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive } from 'vue';
import { List } from '@element-plus/icons-vue';
import ItemCom from './components/ItemCom/index.vue';
import ColumnsTableCom from './components/ColumnsTableCom/index.vue';
import { getRoleList, getModelList, getMenuList } from './api';
import { PageQuery, CurrentInfoType, ModelItemType } from './types';

const columnsTableRef = ref<InstanceType<typeof ColumnsTableCom> | null>(null);
const currentInfo = reactive<CurrentInfoType>({
  role: '',
  model: '',
  app: '',
  menu: '',
});

/**
 * 获取角色
 * @param query 分页参数
 * @param callback 回调函数
 */
const fetchRoleData = async (query: PageQuery, callback: Function) => {
  const res = await getRoleList(query);
  callback(res);
};

/**
 * 获取菜单
 * @param query 分页参数
 * @param callback 回调函数
 */
const fetchMenuData = async (query: PageQuery, callback: Function) => {
  const res = await getMenuList(query);
  callback(res);
};

/**
 * 获取模型列表
 * @param query 分页参数
 * @param callback 回调函数
 */
const fetchModelData = async (query: PageQuery, callback: Function) => {
  const res = await getModelList();
  res.data.forEach((item: ModelItemType) => {
    item.showText = `${item.app}-${item.title}(${item.key})`;
  });
  callback(res);
};

/**
 * 刷新权限表格
 */
const fetchTableData = () => {
  if (currentInfo.role && currentInfo.model && currentInfo.app) {
    columnsTableRef.value?.fetchData(currentInfo);
  }
};

/**
 * 点击事件处理
 * @param type 类型 role | menu | model
 * @param record 选中记录
 */
const handleClick = (type: string, record: any) => {
  if (type === 'role') {
    currentInfo.role = record.id;
  }
  if (type === 'menu') {
    currentInfo.menu = record.id;
  }
  if (type === 'model') {
    currentInfo.model = record.key;
    currentInfo.app = record.app;
  }
  fetchTableData();
};
</script>

<style lang="scss" scoped>
@use '../../../styles/opsflow-global' as *;

.sys-page {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: $of-bg-page;
  overflow: hidden;
}

/* ===== Header ===== */
.columns-header {
  position: relative;
  flex-shrink: 0;
  overflow: hidden;
  background: $of-gradient-hero;
  border-bottom: 1px solid $of-border-light;
  padding: 10px 20px;
}
.columns-header-bg {
  position: absolute;
  inset: 0;
  opacity: 0.04;
  background-image: radial-gradient(circle at 20% 50%, #409EFF 2px, transparent 2px);
  background-size: 40px 40px;
}
.columns-header-inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
}
.columns-header-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $of-gradient-blue;
  color: #fff;
  flex-shrink: 0;
}
.columns-header-text {
  display: flex;
  flex-direction: column;
}
.columns-header-title {
  font-size: 16px;
  font-weight: 700;
  color: $of-text-primary;
  line-height: 1.3;
}
.columns-header-desc {
  font-size: 11px;
  color: $of-text-muted;
  margin-top: 1px;
}

/* ===== Body ===== */
.columns-body {
  flex: 1;
  overflow: hidden;
  padding: 10px 12px;
}
.columns-row {
  height: 100%;
  .el-col {
    height: 100%;
  }
}

/* ===== Card ===== */
.sys-card {
  height: 100%;
  position: relative;
  background: #fff;
  border-radius: $of-radius-card;
  box-shadow: $of-shadow-card;
  padding: 14px 16px;
  overflow: hidden;
}
</style>
