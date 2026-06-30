# OPSflow UI Tab Consolidation

> 提交: 80f9ed95 | 日期: 2026-06-30
> 涉及 App: opsflow
> 类型: 功能新增、重构

---

## 背景

OPSflow 原来有 6+ 个独立路由和页面（`/opsflow_desgner`, `/opsflow-template`, `/opsflow-execution`, `/opsflow-knowledge`, `/opsflow-log`, `/opsflow-webhook`, `/ops_dashboard`, `/opsflow-project`），每个都有自己完整的 hero section。路由分散导致侧边栏菜单臃肿、页面间跳转需完整路由导航。

**目标：** 参考 ITSM 的单路由 tab 模式，将所有 OPSflow 子页面合并为统一的 `/opsflow` 页面。

## 实现方案

### 核心架构

采用 ITSM 的 `designerMode` / `activeTab` 双模式架构：

```
/opsflow → opsflow/index.vue
  ├─ v-if="canvasMode" → 全屏设计画布 (DesignCanvas + AI Chat + dialogs)
  └─ v-else → Hero + Tabs + Body
       ├─ Hero: 标题 + 统计 + 8 个 tab 按钮
       └─ Body: v-show 嵌入 7 个子页面 (embedded=true)
```

**设计器 tab 特殊处理：** 点击"设计器"tab 时设置 `canvasMode = true`，整个页面切换为全屏画布。返回按钮（在 DesignCanvas toolbar 里）设回 `false`。

### 关键代码

**统一页面结构** — `web/src/views/apps/opsflow/index.vue`:

```vue
<!-- Tab mode -->
<div v-else class="opsflow-page">
  <div class="opsflow-hero">
    <!-- 标题 + 统计 + tab 切换 -->
  </div>
  <div class="opsflow-body-wrap">
    <div v-show="activeTab === 'templates'">
      <OpsflowTemplate embedded />
    </div>
    <!-- ... 7 more tabs ... -->
  </div>
</div>
```

**embedded prop** — 7 个子页面统一添加:

```ts
const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })
```

模板中:
```vue
<div v-if="!embedded" class="xxx-hero">...</div>  <!-- 嵌入时隐藏hero -->
<div class="xxx-body">...</div>                      <!-- 始终显示 -->
```

**返回按钮集成到 DesignCanvas toolbar** — `DesignCanvas.vue`:

```ts
// 新增 props/emits
const props = defineProps<{ showBack?: boolean; ... }>()
const emit = defineEmits<{ back: []; ... }>()
```

Toolbar 模板中:
```vue
<template v-if="showBack">
  <el-button text size="small" @click="$emit('back')">
    <el-icon><ArrowLeft /></el-icon> 返回
  </el-button>
  <div class="toolbar-divider" />
</template>
```

### 数据流

```
menu seed (/opsflow) → Menu(DB) → /api/system/menu/web_router/
  → backEnd.ts → addRoute → router
  → 用户点击 → activeTab/canvasMode 切换
  → v-show 激活对应子页面
  → 子页面(embedded=true) 隐藏自身 hero, 展示 body
```

### 设计决策

1. **v-show 而非 v-if** — 保持各 tab 组件实例存活，切换时保留滚动位置和状态，与 ITSM 一致
2. **embedded prop 而非新组件** — 最小改动。子页面只需加一个 prop，不需要提取 body 为独立组件
3. **返回按钮放 toolbar 而非独立定位** — 参考 ITSM DesignerToolbar 模式，跟画布缩放/保存等按钮在同一行
4. **菜单种子统一** — `seed_opsflow.py` 从 6 个独立 menu leaf 合并为一个 `/opsflow` 入口，归入"运维平台" catalog

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/opsflow/index.vue` | 重写 — 统一 tab 容器，hero + tabs + 7 子页面嵌入 |
| `web/src/views/apps/opsflow/components/canvas/DesignCanvas.vue` | showBack prop + back emit，返回按钮集成到 toolbar |
| `web/src/views/apps/opsflow-*/index.vue` (7 files) | embedded prop 支持 |
| `backend/opsflow/management/commands/seed_opsflow.py` | 菜单种子合并为单一入口 |

## 使用方式

- 访问 `/opsflow` → 默认显示"模板中心" tab
- 点击 hero tab 切换子页面
- 点击"设计器" tab → 进入全屏画布模式
- 画布 toolbar 左侧"返回"按钮 → 回到 tab 视图
- URL query 支持: `/opsflow?tab=executions`
