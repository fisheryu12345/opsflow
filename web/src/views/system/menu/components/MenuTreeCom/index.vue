<template>
  <div class="menu-tree-com">
    <!-- Search filter / 搜索过滤 -->
    <div class="mtc-filter">
      <el-input
        v-model="filterVal"
        :prefix-icon="Search"
        :placeholder="$t('message.menuPage.searchMenuPlaceholder')"
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
        class="g-tree"
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
      <el-button size="small" type="primary" v-auth="'menu:Create'" @click="handleUpdateMenu('create')">
        <el-icon><Plus /></el-icon>
      </el-button>
      <el-button size="small" v-auth="'menu:Update'" @click="handleUpdateMenu('update')" :disabled="!treeSelectMenu.id">
        <el-icon><Edit /></el-icon>
      </el-button>
      <el-button size="small" v-auth="'menu:MoveUp'" @click="handleSort('up')" :disabled="!treeSelectMenu.id">
        <el-icon><Top /></el-icon>
      </el-button>
      <el-button size="small" v-auth="'menu:MoveDown'" @click="handleSort('down')" :disabled="!treeSelectMenu.id">
        <el-icon><Bottom /></el-icon>
      </el-button>
      <el-button size="small" type="danger" v-auth="'menu:Delete'" @click="handleDeleteMenu()" :disabled="!treeSelectMenu.id">
        <el-icon><Delete /></el-icon>
      </el-button>
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
  label: 'name_display',
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

const filterNode = (value: string, data: any) => {
  if (!value) return true;
  const raw = toRaw(data);
  return (raw.name + (raw.name_display || '')).indexOf(value) !== -1;
};

const handleTreeLoad = (node: Node, resolve: Function) => {
  if (node.level !== 0) {
    lazyLoadMenu({ parent: node.data.id }).then((res: APIResponseData) => {
      resolve(res.data);
    });
  }
};

const handleNodeClick = (record: MenuTreeItemType, node: Node) => {
  treeSelectMenu.value = record;
  treeSelectNode.value = node;
  emit('treeClick', record);
};

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

const handleDeleteMenu = () => {
  if (!treeSelectMenu.value.id) {
    warningNotification('Please select a menu! / 请选择菜单！');
    return;
  }
  emit('deleteDept', treeSelectMenu.value.id, () => {
    treeSelectMenu.value = {};
  });
};

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
@use '/@/styles/global' as *;

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

.mtc-node-label {
  font-size: 13px;
  display: inline-flex;
  align-items: center;
}

.mtc-node-active {
  color: $g-text-primary;
}

.mtc-node-disabled {
  color: #f56c6c !important;
  text-decoration: line-through;
  opacity: 0.7;
}

/* ===== Action Buttons ===== */
.mtc-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid $g-border-light;
  background: $g-bg-card;
  flex-shrink: 0;
}
</style>

<style lang="scss">
@use '/@/styles/global' as *;

/* Global tree overrides / 全局树样式覆盖 */
.menu-tree-com .g-tree,
.mtc-tree-wrap .el-tree {
  background: transparent;

  .el-tree-node__content {
    height: 34px !important;
    border-radius: 6px;
    transition: background $g-transition-default;

    &:hover {
      background: $g-bg-light-blue;
    }
  }

  .el-tree-node.is-current > .el-tree-node__content {
    background: $g-bg-light-blue;
    color: $g-color-primary;
  }

  .el-tree-node__expand-icon {
    font-size: 14px;
    color: $g-text-muted;
    padding: 0;
    margin-right: 4px;
    margin-left: 20px;
    transition: transform $g-transition-default;

    &.expanded {
      transform: rotate(0deg);
      color: $g-color-primary;
    }

    &.is-leaf {
      margin-left: 4px;
      visibility: visible;
      &::before { display: none; }
    }

    svg { display: none !important; height: 0; width: 0; }
  }

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
