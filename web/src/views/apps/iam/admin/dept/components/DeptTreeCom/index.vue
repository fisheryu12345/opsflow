<template>
  <div class="dtc-wrap">
    <div class="dtc-head">
      <span class="dtc-head-icon">
        <el-icon :size="15"><OfficeBuilding /></el-icon>
      </span>
      <span class="dtc-head-title">{{ $t('message.menuPage.deptArch') }}</span>
      <el-tooltip content="显示/隐藏人数" placement="bottom">
        <el-icon :size="14" class="dtc-head-action" @click="showTotalNum = !showTotalNum">
          <View v-if="!showTotalNum" /><Hide v-else />
        </el-icon>
      </el-tooltip>
    </div>

    <el-input
      v-model="filterVal"
      :prefix-icon="Search"
      :placeholder="$t('message.menuPage.deptSearch')"
      clearable
      size="small"
      class="dtc-filter"
    />

    <div class="dtc-tree">
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="treeProps"
        :filter-node-method="onFilter"
        :load="onLoad"
        lazy
        :indent="30"
        @node-click="onClick"
        highlight-current
        node-key="id"
        :default-expand-all="false"
      >
        <template #default="{ node, data }">
          <element-tree-line :node="node" :showLabelLine="false" :indent="30">
            <span class="dtc-node">
              <SvgIcon name="iconfont icon-shouye" :color="data.status ? '#409eff' : '#c0c4cc'" />
              <span :class="{ 'dtc-node-disabled': !data.status }">{{ node.label }}</span>
              <span v-if="showTotalNum" class="dtc-node-count">{{ data.dept_user_count || 0 }}人</span>
            </span>
          </element-tree-line>
        </template>
      </el-tree>
    </div>

    <div class="dtc-actions">
      <el-tooltip :content="$t('message.menuPage.deptNew')" placement="top">
        <el-button text :icon="Plus" circle size="small" @click="emitUpdate('create')" />
      </el-tooltip>
      <el-tooltip :content="$t('message.menuPage.deptEdit')" placement="top">
        <el-button text :icon="Edit" circle size="small" @click="emitUpdate('update')" />
      </el-tooltip>
      <el-tooltip :content="$t('message.menuPage.deptMoveUp')" placement="top">
        <el-button text :icon="Top" circle size="small" @click="handleSort('up')" />
      </el-tooltip>
      <el-tooltip :content="$t('message.menuPage.deptMoveDown')" placement="top">
        <el-button text :icon="Bottom" circle size="small" @click="handleSort('down')" />
      </el-tooltip>
      <el-tooltip :content="$t('message.menuPage.deptDelete')" placement="top">
        <el-button text type="danger" :icon="Delete" circle size="small" @click="handleDelete" />
      </el-tooltip>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, toRaw, h } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElTree } from 'element-plus';
import { getElementLabelLine } from 'element-tree-line';
import { Search, OfficeBuilding, View, Hide, Plus, Edit, Top, Bottom, Delete } from '@element-plus/icons-vue';
import { lazyLoadDept, deptMoveUp, deptMoveDown } from '../../api';
import { warningNotification } from '/@/utils/message';
import { TreeItemType, APIResponseData } from '../../types';
import type Node from 'element-plus/es/components/tree/src/model/node';

const { t } = useI18n();

const ElementTreeLine = getElementLabelLine(h);

const props = withDefaults(defineProps<{ treeData: TreeItemType[] }>(), { treeData: () => [] });
const emit = defineEmits(['treeClick', 'deleteDept', 'updateDept']);

const treeProps = {
  children: 'children', label: 'name',
  isLeaf: (data: TreeItemType) => !data.hasChild,
};

const filterVal = ref('');
const showTotalNum = ref(false);
let sortLock = false;
const selectedDept = ref<TreeItemType>({});
const selectedNode = ref<Node | null>(null);
const treeRef = ref<InstanceType<typeof ElTree>>();

watch(filterVal, v => treeRef.value!.filter(v));
const onFilter = (v: string, d: TreeItemType) => !v || toRaw(d).name?.indexOf(v) !== -1;
const onLoad = (node: Node, resolve: Function) => {
  if (node.level !== 0) lazyLoadDept({ parent: node.data.id }).then((r: APIResponseData) => resolve(r.data));
};
const onClick = (record: TreeItemType, node: Node) => { selectedDept.value = record; selectedNode.value = node; emit('treeClick', record); };

const emitUpdate = (type: string) => {
  if (type === 'update' && !selectedDept.value.id) { warningNotification(t('message.menuPage.deptSelectFirst')); return; }
  emit('updateDept', type, type === 'update' ? selectedDept.value : undefined);
};

const handleDelete = () => {
  if (!selectedDept.value.id) { warningNotification(t('message.menuPage.deptSelectFirst')); return; }
  emit('deleteDept', selectedDept.value.id, () => { selectedDept.value = {}; });
};

const handleSort = async (dir: 'up' | 'down') => {
  if (!selectedDept.value.id) { warningNotification(t('message.menuPage.deptSelectFirst')); return; }
  if (sortLock) return;
  const siblings = selectedNode.value?.parent.childNodes || [];
  const idx = siblings.findIndex((i: any) => i.data.id === selectedDept.value.id);
  const node = siblings.find((i: any) => i.data.id === selectedDept.value.id);
  if (!node || (dir === 'up' && idx === 0) || (dir === 'down' && idx >= siblings.length - 1)) return;
  siblings.splice(dir === 'up' ? idx - 1 : idx + 2, 0, node as any);
  siblings.splice(dir === 'up' ? idx + 1 : idx, 1);
  sortLock = true;
  await (dir === 'up' ? deptMoveUp({ dept_id: selectedDept.value.id }) : deptMoveDown({ dept_id: selectedDept.value.id }));
  sortLock = false;
};

defineExpose({ treeRef });
</script>

<style scoped lang="scss">
$p: #409eff; $st: #303133; $s2: #909399; $b: #ebeef5;
.dtc-wrap {
  height: 100%; display: flex; flex-direction: column;
  padding: 14px; box-sizing: border-box;
}
.dtc-head {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 10px; font-size: 14px; font-weight: 600; color: $st;
  .dtc-head-action { margin-left: auto; cursor: pointer; transition: color .2s; &:hover { color: $p; } }
}
.dtc-filter { margin-bottom: 8px; }
.dtc-tree {
  flex: 1; overflow-y: auto;
  :deep(.el-tree-node__content) { height: 30px; }
}
.dtc-node {
  .dtc-node-disabled { color: #c0c4cc; text-decoration: line-through; }
  .dtc-node-count { font-size: 11px; color: $s2; margin-left: 4px; }
}
.dtc-actions {
  display: flex; align-items: center; justify-content: space-around;
  padding: 8px 2px 0; margin-top: 6px; border-top: 1px solid $b; flex-shrink: 0;
}
</style>

<style lang="scss">
.dtc-tree {
  .el-tree-node__content > .el-tree-node__expand-icon { padding: 0; margin-right: 4px; margin-left: 14px; }
  .el-tree .el-tree-node__expand-icon.expanded { transform: rotate(0deg); }
  .el-tree .el-tree-node__expand-icon:before {
    background: url('../../../../../assets/img/menu-tree-show-icon.png') no-repeat center / 100%;
    content: ''; display: block; width: 20px; height: 20px;
  }
  .el-tree .el-tree-node__expand-icon.expanded:before { background-image: url('../../../../../assets/img/menu-tree-hidden-icon.png'); }
  .el-tree .is-leaf.el-tree-node__expand-icon::before { background: none !important; width: 16px; height: 16px; }
}
</style>
