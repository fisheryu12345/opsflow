<template>
  <div class="menu-tree-com">
    <!-- Search filter / 搜索过滤 -->
    <div class="mtc-filter">
      <el-input
        v-model="filterVal"
        :prefix-icon="Search"
        placeholder="Search menu name / 请输入菜单名称"
        size="default"
        clearable
      />
    </div>

    <!-- Tree container / 树容器 -->
    <div class="mtc-tree-wrap">
      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="defaultTreeProps"
        :filter-node-method="filterNode"
        :load="handleTreeLoad"
        lazy
        :indent="45"
        @node-click="handleNodeClick"
        highlight-current
        node-key="id"
        class="of-tree"
      >
        <template #default="{ node, data }">
          <element-tree-line :node="node" :showLabelLine="false" :indent="32">
            <span v-if="data.status" class="mtc-node-label mtc-node-active">
              <SvgIcon :name="node.data.icon" color="var(--el-color-primary)" />
              &nbsp;{{ node.label }}
            </span>
            <span v-else class="mtc-node-label mtc-node-disabled">
              <SvgIcon :name="node.data.icon" />
              &nbsp;{{ node.label }}
            </span>
          </element-tree-line>
        </template>
      </el-tree>
    </div>

    <!-- Action buttons / 操作按钮 -->
    <div class="mtc-actions">
      <el-tooltip effect="dark" content="Add / 新增" placement="top">
        <el-icon size="16" v-auth="'menu:Create'" @click="handleUpdateMenu('create')" class="mtc-action-icon">
          <Plus />
        </el-icon>
      </el-tooltip>

      <el-tooltip effect="dark" content="Edit / 编辑" placement="top">
        <el-icon size="16" v-auth="'menu:Update'" @click="handleUpdateMenu('update')" class="mtc-action-icon">
          <Edit />
        </el-icon>
      </el-tooltip>

      <el-tooltip effect="dark" content="Move Up / 上移" placement="top">
        <el-icon size="16" v-auth="'menu:MoveUp'" @click="handleSort('up')" class="mtc-action-icon">
          <Top />
        </el-icon>
      </el-tooltip>

      <el-tooltip effect="dark" content="Move Down / 下移" placement="top">
        <el-icon size="16" v-auth="'menu:MoveDown'" @click="handleSort('down')" class="mtc-action-icon">
          <Bottom />
        </el-icon>
      </el-tooltip>

      <el-tooltip effect="dark" content="Delete / 删除" placement="top">
        <el-icon size="16" v-auth="'menu:Delete'" @click="handleDeleteMenu()" class="mtc-action-icon mtc-action-danger">
          <Delete />
        </el-icon>
      </el-tooltip>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, toRaw, watch, h } from 'vue';
import { ElTree } from 'element-plus';
import { getElementLabelLine } from 'element-tree-line';
import { Search, Plus, Edit, Top, Bottom, Delete } from '@element-plus/icons-vue';
import SvgIcon from '/@/components/svgIcon/index.vue';
import { lazyLoadMenu, menuMoveUp, menuMoveDown } from '../../api';
import { warningNotification } from '/@/utils/message';
import { TreeTypes, MenuTreeItemType, APIResponseData } from '../../types';
import type Node from 'element-plus/es/components/tree/src/model/node';

interface IProps {
  treeData: TreeTypes[];
}

const ElementTreeLine = getElementLabelLine(h);

const defaultTreeProps: any = {
  children: 'children',
  label: 'name',
  icon: 'icon',
  isLeaf: (data: TreeTypes[], node: Node) => {
    if (node.data.is_catalog) {
      return false;
    } else {
      return true;
    }
  },
};

const treeRef = ref<InstanceType<typeof ElTree>>();

withDefaults(defineProps<IProps>(), {
  treeData: () => [],
});
const emit = defineEmits(['treeClick', 'deleteDept', 'updateDept']);

let filterVal = ref('');
let sortDisable = ref(false);
let treeSelectMenu = ref<Partial<MenuTreeItemType>>({});
let treeSelectNode = ref<Node | null>(null);

watch(filterVal, (val) => {
  treeRef.value!.filter(val);
});

/**
 * Tree filter / 树的搜索事件
 */
const filterNode = (value: string, data: any) => {
  if (!value) return true;
  return toRaw(data).name.indexOf(value) !== -1;
};

/**
 * Lazy load / 树的懒加载
 */
const handleTreeLoad = (node: Node, resolve: Function) => {
  if (node.level !== 0) {
    lazyLoadMenu({ parent: node.data.id }).then((res: APIResponseData) => {
      resolve(res.data);
    });
  }
};

/**
 * Tree click / 树的点击事件
 */
const handleNodeClick = (record: MenuTreeItemType, node: Node) => {
  treeSelectMenu.value = record;
  treeSelectNode.value = node;
  emit('treeClick', record);
};

/**
 * Edit button click / 点击左侧编辑按钮
 */
const handleUpdateMenu = (type: string) => {
  if (type === 'update') {
    if (!treeSelectMenu.value.id) {
      warningNotification('Please select a menu! / 请选择菜单！');
      return;
    }
    emit('updateDept', type, treeSelectMenu.value);
  } else {
    emit('updateDept', type);
  }
};

/**
 * Delete menu / 删除菜单
 */
const handleDeleteMenu = () => {
  if (!treeSelectMenu.value.id) {
    warningNotification('Please select a menu! / 请选择菜单！');
    return;
  }
  emit('deleteDept', treeSelectMenu.value.id, () => {
    treeSelectMenu.value = {};
  });
};

/**
 * Sort move / 移动操作
 */
const handleSort = async (type: string) => {
  if (!treeSelectMenu.value.id) {
    warningNotification('Please select a menu! / 请选择菜单！');
    return;
  }
  if (sortDisable.value) return;

  const parentList = treeSelectNode.value?.parent.childNodes || [];
  const index = parentList.findIndex((i) => i.data.id === treeSelectMenu.value.id);
  const record = parentList.find((i) => i.data.id === treeSelectMenu.value.id);

  if (type === 'up') {
    if (index === 0) return;
    parentList.splice(index - 1, 0, record as any);
    parentList.splice(index + 1, 1);
    sortDisable.value = true;
    await menuMoveUp({ menu_id: treeSelectMenu.value.id });
    sortDisable.value = false;
  }
  if (type === 'down') {
    parentList.splice(index + 2, 0, record as any);
    parentList.splice(index, 1);
    sortDisable.value = true;
    await menuMoveDown({ menu_id: treeSelectMenu.value.id });
    sortDisable.value = false;
  }
};

defineExpose({
  treeRef,
});
</script>

<style lang="scss" scoped>
@use '../../../../apps/opsflow/styles/opsflow-global' as *;

.menu-tree-com {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.mtc-filter {
  padding: 12px 16px;
  flex-shrink: 0;
}

.mtc-tree-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

/* ===== Tree Node Labels ===== */
.mtc-node-label {
  font-size: 13px;
  display: inline-flex;
  align-items: center;
}

.mtc-node-active {
  color: $of-text-primary;
}

.mtc-node-disabled {
  color: #f56c6c !important;
  text-decoration: line-through;
  opacity: 0.7;
}

/* ===== Action Buttons ===== */
.mtc-actions {
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 0 16px;
  border-top: 1px solid $of-border-light;
  background: $of-bg-card;
}

.mtc-action-icon {
  cursor: pointer;
  color: $of-color-primary;
  padding: 6px;
  border-radius: 6px;
  transition: background $of-transition-default, transform $of-transition-default;

  &:hover {
    background: $of-bg-light-blue;
    transform: translateY(-1px);
  }

  &:active {
    transform: scale(0.92);
  }
}

.mtc-action-danger {
  color: #f56c6c;

  &:hover {
    background: $of-bg-danger;
  }
}
</style>

<style lang="scss">
@use '../../../../apps/opsflow/styles/opsflow-global' as *;

/* Global tree overrides / 全局树样式覆盖 */
.menu-tree-com .of-tree,
.mtc-tree-wrap .el-tree {
  background: transparent;

  .el-tree-node__content {
    height: 34px !important;
    border-radius: 6px;
    transition: background $of-transition-default;

    &:hover {
      background: $of-bg-light-blue;
    }
  }

  .el-tree-node.is-current > .el-tree-node__content {
    background: $of-bg-light-blue;
    color: $of-color-primary;
  }

  .el-tree-node__expand-icon {
    font-size: 14px;
    color: $of-text-muted;
    padding: 0;
    margin-right: 4px;
    margin-left: 20px;
    transition: transform $of-transition-default;

    &.expanded {
      transform: rotate(0deg);
      color: $of-color-primary;
    }

    &.is-leaf {
      margin-left: 4px;
      visibility: visible;

      &::before {
        display: none;
      }
    }

    svg {
      display: none !important;
      height: 0;
      width: 0;
    }
  }

  /* Tree expand/collapse custom icons */
  .el-tree-node__expand-icon:before {
    background: url('../../../../../assets/img/menu-tree-show-icon.png') no-repeat center / 100%;
    content: '';
    display: block;
    width: 22px;
    height: 22px;
  }

  .el-tree-node__expand-icon.expanded:before {
    background: url('../../../../../assets/img/menu-tree-hidden-icon.png') no-repeat center / 100%;
  }

  .el-tree-node__expand-icon.is-leaf:before {
    background: none !important;
    width: 18px;
    height: 18px;
  }
}
</style>
