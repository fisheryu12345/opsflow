<template>
  <div class="dtc-wrap">
    <div class="dtc-header">
      <el-icon :size="16" color="#409eff"><OfficeBuilding /></el-icon>
      <span class="dtc-title">部门架构</span>
      <el-tooltip content="显示/隐藏人数" placement="bottom">
        <el-icon :size="15" color="#909399" class="dtc-header-action" @click="showTotalNum = !showTotalNum">
          <View v-if="!showTotalNum" /><Hide v-else />
        </el-icon>
      </el-tooltip>
    </div>

    <el-input v-model="filterVal" :prefix-icon="Search" placeholder="搜索部门名称..." clearable size="small" style="margin-bottom:8px" />

    <div class="dtc-tree-area">
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="defaultTreeProps"
        :filter-node-method="handleFilterTreeNode"
        :load="handleLoadNode"
        lazy
        :indent="36"
        @node-click="handleNodeClick"
        highlight-current
        node-key="id"
        default-expand-all
      >
        <template #default="{ node, data }">
          <element-tree-line :node="node" :showLabelLine="false" :indent="32">
            <span class="dtc-node">
              <SvgIcon name="iconfont icon-shouye" :color="data.status ? '#409eff' : '#c0c4cc'" />
              <span :class="{ 'dtc-node-disabled': !data.status }">{{ node.label }}</span>
              <span v-if="showTotalNum" class="dtc-node-count">（{{ data.dept_user_count }}人）</span>
            </span>
          </element-tree-line>
        </template>
      </el-tree>
    </div>

    <div class="dtc-actions">
      <el-tooltip content="新增" placement="top"><el-button text type="primary" :icon="Plus" circle size="small" @click="handleUpdateMenu('create')" /></el-tooltip>
      <el-tooltip content="编辑" placement="top"><el-button text type="primary" :icon="Edit" circle size="small" @click="handleUpdateMenu('update')" /></el-tooltip>
      <el-tooltip content="上移" placement="top"><el-button text type="primary" :icon="Top" circle size="small" @click="handleSort('up')" /></el-tooltip>
      <el-tooltip content="下移" placement="top"><el-button text type="primary" :icon="Bottom" circle size="small" @click="handleSort('down')" /></el-tooltip>
      <el-tooltip content="删除" placement="top"><el-button text type="danger" :icon="Delete" circle size="small" @click="handleDeleteDept" /></el-tooltip>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, toRaw, h } from 'vue';
import { ElTree } from 'element-plus';
import { getElementLabelLine } from 'element-tree-line';
import { Search, OfficeBuilding, View, Hide, Plus, Edit, Top, Bottom, Delete } from '@element-plus/icons-vue';
import { lazyLoadDept, deptMoveUp, deptMoveDown } from '../../api';
import { warningNotification } from '/@/utils/message';
import { TreeItemType, APIResponseData } from '../../types';
import type Node from 'element-plus/es/components/tree/src/model/node';

const ElementTreeLine = getElementLabelLine(h);

interface IProps { treeData: TreeItemType[]; }
const props = withDefaults(defineProps<IProps>(), { treeData: () => [] });
const emit = defineEmits(['treeClick', 'deleteDept', 'updateDept']);

const defaultTreeProps = {
  children: 'children', label: 'name',
  isLeaf: (data: TreeItemType) => !data.hasChild,
};

const filterVal = ref('');
const showTotalNum = ref(false);
const sortDisable = ref(false);
const treeSelectDept = ref<TreeItemType>({});
const treeSelectNode = ref<Node | null>(null);
const treeRef = ref<InstanceType<typeof ElTree>>();

watch(filterVal, (val) => treeRef.value!.filter(val));

const handleFilterTreeNode = (value: string, data: TreeItemType) => !value || toRaw(data).name?.indexOf(value) !== -1;

const handleLoadNode = (node: Node, resolve: Function) => {
  if (node.level !== 0) lazyLoadDept({ parent: node.data.id }).then((res: APIResponseData) => resolve(res.data));
};

const handleNodeClick = (record: TreeItemType, node: Node) => { treeSelectDept.value = record; treeSelectNode.value = node; emit('treeClick', record); };

const handleUpdateMenu = (type: string) => {
  if (type === 'update') {
    if (!treeSelectDept.value.id) { warningNotification('请先选择部门！'); return; }
    emit('updateDept', type, treeSelectDept.value);
  } else { emit('updateDept', type); }
};

const handleDeleteDept = () => {
  if (!treeSelectDept.value.id) { warningNotification('请先选择部门！'); return; }
  emit('deleteDept', treeSelectDept.value.id, () => { treeSelectDept.value = {}; });
};

const handleSort = async (type: string) => {
  if (!treeSelectDept.value.id) { warningNotification('请先选择部门！'); return; }
  if (sortDisable.value) return;
  const parentList = treeSelectNode.value?.parent.childNodes || [];
  const index = parentList.findIndex(i => i.data.id === treeSelectDept.value.id);
  const record = parentList.find(i => i.data.id === treeSelectDept.value.id);
  if (type === 'up' && index !== 0) {
    parentList.splice(index - 1, 0, record as any);
    parentList.splice(index + 1, 1);
    sortDisable.value = true;
    await deptMoveUp({ dept_id: treeSelectDept.value.id });
    sortDisable.value = false;
  }
  if (type === 'down' && index < parentList.length - 1) {
    parentList.splice(index + 2, 0, record as any);
    parentList.splice(index, 1);
    sortDisable.value = true;
    await deptMoveDown({ dept_id: treeSelectDept.value.id });
    sortDisable.value = false;
  }
};

defineExpose({ treeRef });
</script>

<style scoped lang="scss">
$of-color-primary: #409eff;
$of-bg-light-blue: #ecf5ff;
$of-bg-card-hover: #f5f9ff;
$of-text-primary: #303133;
$of-text-secondary: #909399;
$of-border-light: #ebeef5;

.dtc-wrap {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 14px;
  box-sizing: border-box;
}

.dtc-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 600;
  color: $of-text-primary;

  .dtc-header-action {
    margin-left: auto;
    cursor: pointer;
    transition: color 0.2s;
    &:hover { color: $of-color-primary; }
  }
}

.dtc-tree-area {
  flex: 1;
  overflow-y: auto;

  :deep(.el-tree-node__content) {
    height: 30px;
  }
}

.dtc-node {
  .dtc-node-disabled {
    color: #c0c4cc;
    text-decoration: line-through;
  }
  .dtc-node-count {
    font-size: 11px;
    color: $of-text-secondary;
    margin-left: 2px;
  }
}

.dtc-actions {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 10px 4px 0;
  margin-top: 8px;
  border-top: 1px solid $of-border-light;
  flex-shrink: 0;
}
</style>

<style lang="scss">
.dtc-tree-area {
  .el-tree-node__expand-icon {
    font-size: 14px;
  }
  .el-tree-node__content > .el-tree-node__expand-icon {
    padding: 0;
    margin-right: 4px;
    margin-left: 16px;
  }
  .el-tree .el-tree-node__expand-icon.expanded {
    transform: rotate(0deg);
  }
  .el-tree .el-tree-node__expand-icon:before {
    background: url('../../../../../assets/img/menu-tree-show-icon.png') no-repeat center / 100%;
    content: '';
    display: block;
    width: 22px;
    height: 22px;
  }
  .el-tree .el-tree-node__expand-icon.expanded:before {
    background: url('../../../../../assets/img/menu-tree-hidden-icon.png') no-repeat center / 100%;
  }
  .el-tree .is-leaf.el-tree-node__expand-icon::before {
    background: none !important;
    width: 18px;
    height: 18px;
  }
}
</style>
