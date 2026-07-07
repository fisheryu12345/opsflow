# OPSflow Frontend Style Guide

All OPSflow Vue components should follow these conventions for visual consistency.

**后续向导对话框参考:** `SubmitWizardDialog.vue` — 多步骤弹窗的 HTML/SCSS/动画标准实现。

---

## SCSS

**唯一入口：** `@use 'styles/global' as *;`
```scss
<style lang="scss" scoped>
@use 'styles/global' as *;
</style>
```

**设计令牌 — 使用 `$g-*` 变量，禁止硬编码颜色/阴影/圆角**

| 常用变量 | 值 | 用途 |
|----------|-----|------|
| `$g-bg-page` | `#f0f2f5` | 页面背景 |
| `$g-color-primary` | `#409EFF` | Element 蓝色主色 |
| `$g-text-primary` | `#303133` | 主文字色 |
| `$g-text-secondary` | `#666` | 次要文字色 |
| `$g-text-muted` | `#909399` | 辅助文字/placeholder |
| `$g-border-light` | `#ebeef5` | 浅边框（分割线） |
| `$g-border-card` | `#f0f0f0` | 卡片边框 |
| `$g-radius` | `10px` | 卡片/大圆角 |
| `$g-radius-sm` | `8px` | 小组件圆角 |
| `$g-shadow-card` | `0 1px 4px rgba(0,0,0,0.06)` | 卡片阴影 |
| `$g-shadow-hover` | `0 4px 12px rgba(0,0,0,0.08)` | 悬浮阴影 |
| `$g-bg-header` | `#f5f7fa` | 表格列头背景 |
| `$g-bg-success` | `#f0f9eb` | 成功背景 |
| `$g-bg-warning` | `#fdf6ec` | 警告背景 |
| `$g-bg-danger` | `#fef0f0` | 危险背景 |
| `$g-bg-light-blue` | `#ecf5ff` | 浅蓝色背景 |

**完整变量表见** `web/src/styles/_tokens.scss`

**通用 class — 使用 `.g-*` 前缀**

| class | 用途 |
|-------|------|
| `.g-card` | 标准卡片容器（背景白、圆角、阴影） |
| `.g-card-header` | 卡片标题栏（带下分割线） |
| `.g-card-body` | 卡片内容区（内边距） |
| `.g-fade-in-up` | 入场动画（淡入上移） |
| `.g-stagger-item` | 列表交错动画 |
| `.g-status-tag` | 状态标签（active/inactive/pending） |

**Mixin — `@include g-*`**

| mixin | 用途 |
|-------|------|
| `g-hover-lift` | 悬浮上移 + 阴影加深 |
| `g-hover-shift` | 悬浮右移 |
| `g-dialog-header` | 弹窗标题栏样式 |
| `g-dialog-body` | 弹窗内容区内边距 |
| `g-dialog-footer` | 弹窗底部按钮区 |
| `g-icon-circle` | 渐变图标圆形背景 |
| `g-section-header` | 区块标题栏 |

**Dialog 规范：** 添加 class `opsflow-dialog`（header/body/footer 自动样式化）

---

## Hero Section 规范（全线统一）

所有 App 页面顶部 hero banner 必须使用 `g-hero-*` mixin，禁止硬编码 hero 字号/间距/颜色。

### 标准 Hero 模板

```scss
.my-hero       { @include g-hero-container; }
.my-hero-bg    { @include g-hero-bg-dots; }
.my-hero-inner { @include g-hero-inner; }
.my-hero-title { @include g-hero-title; }
.my-hero-subtitle { @include g-hero-subtitle; }
```

### 统计项

```scss
.my-hero-stats { flex: 0 0 auto; display: flex; align-items: center; }
.my-stat-value   { @include g-hero-stat-value; }
.my-stat-label   { @include g-hero-stat-label; }
.my-stat-divider { @include g-hero-stat-divider; }
```

### Tab 式 Hero

```scss
.my-hero-tabs { @include g-hero-tabs; }
.my-hero-tab  { @include g-hero-tab; }
```

### Hero Token 对照表

| Token | 值 | 对应 Mixin |
|-------|-----|-----------|
| `$g-hero-title-size` | **22px** / 800 weight | `g-hero-title` |
| `$g-hero-subtitle-size` / `$g-hero-subtitle-color` | **11px** / `rgba(255,255,255,0.5)` | `g-hero-subtitle` |
| `$g-hero-stat-value-size` / `$g-hero-stat-value-weight` | **18px** / 700 | `g-hero-stat-value` |
| `$g-hero-stat-label-size` / `$g-hero-stat-label-color` | **10px** / `rgba(255,255,255,0.45)` | `g-hero-stat-label` |
| `$g-hero-divider-height` / `$g-hero-divider-color` | **24px** / `rgba(255,255,255,0.1)` | `g-hero-stat-divider` |
| `$g-hero-inner-padding` | **14px 24px** | `g-hero-inner` |
| `$g-hero-inner-gap` | **16px** | `g-hero-inner` |
| `$g-hero-dot-opacity` / `$g-hero-dot-size` | **0.06** / **40px** | `g-hero-bg-dots` |

### 渐变背景

- 默认深蓝：变量 `$g-gradient-hero`（`#1a1a2e → #16213e → #0f3460`），mixin `g-hero-container`
- 绿色变体（job-platform 等）：`$g-gradient-hero-green`

### 约束规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | **必须用 mixin** | hero 标题/副标题/统计值/分隔线的字号和颜色禁止硬编码，一律 `@include g-hero-*` |
| 2 | **禁止扩高** | hero-inner padding 统一 `14px 24px`（portal/opsflow-* 已拉齐），禁止额外扩高 |
| 3 | **统计分隔线** | 统一 `$g-hero-divider-height: 24px`，stat-item padding `0 14px` |
| 4 | **tabs 上拉** | 有 tabs 的 hero 需要 `margin-top: -4px` 吸附到 hero 底部 |
| 5 | **tab 内容左对齐** | `g-hero-tab` mixin 使用 `padding: 10px 16px 10px 0`（无左侧 padding），因为 tabs 容器 `padding: 0 24px` 已与 hero-inner 对齐。**禁止给 hero-tab 加左侧 padding**，否则 tab 内容会比标题偏右。如确需 tab 间距，用 `margin-right` 或容器 `gap` 实现 |
| 6 | **已对齐页面** | portal / opsflow / opsflow-dashboard / itsm / integration / cmdb / job-platform / iam / opsflow-log / opsflow-knowledge / opsflow-approval / opsflow-webhook / opsflow-template / open-api / opsagent |

---

## Tab 懒加载规范（`useTabLazyLoad`）

所有带 Tab 切换的 APP 页面**必须**使用 `useTabLazyLoad` composable，禁止所有 Tab 在 `onMounted` 时全部挂载。

### 核心模式

```html
<!-- 每个 tab 区块：v-if 控制挂载，v-show 控制显示 -->
<div v-if="isVisited('tickets')" v-show="activeTab === 'tickets'" class="app-section">
  <!-- inline content or component -->
</div>
```

- **`v-if`** — 懒挂载核心。组件/内联内容仅在首次访问时创建 DOM、触发 `onMounted`
- **`v-show`** — 已挂载 tab 的显示/隐藏切换，无额外开销
- **`isVisited()`** — composable 提供的访问追踪函数，语义清晰

### Composable API

```ts
import { useTabLazyLoad } from '/@/composables/useTabLazyLoad'

const { isVisited } = useTabLazyLoad({
  tabs: ['dashboard', 'tickets', 'workflows', ...],  // 所有 tab key
  activeTab,                                          // Ref<string> 当前 active tab
  onTabActivated: (tab, isFirstVisit) => {            // 首次访问时触发数据加载
    if (!isFirstVisit) return
    if (tab === 'tickets') loadTickets()
    else if (tab === 'workflows') loadWorkflows()
    // 组件 tab 由子组件 onMounted 自动处理，无需手动加载
  },
  resetOn: projectChangedTrigger,                     // 可选：外部重置（项目切换）
})
```

### 使用场景

| 场景 | 做法 |
|------|------|
| **组件 Tab** | 每个 tab 必须是独立 `.vue` 组件；数据在子组件 `onMounted` / `watch(active)` 中自动加载 |
| **项目切换** | 传入 `resetOn` ref → composable 清空 `visitedTabs` → 当前 tab 重新挂载 |
| **默认 Tab** | composable 在 `onMounted` 时自动标记 `activeTab` 为 visited |

### 子 Tab 组件模式（强制）

**所有子 Tab 必须使用独立组件，禁止在父 `index.vue` 中内联渲染。** 每个子 Tab 组件遵守以下契约：

```vue
<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'

// 1. Props
const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })

// 2. Hero stats reporting
const { reportStats: updateHeroStats } = useHeroConsumer()

// 3. Data loading — on mount + on reactivation
onMounted(() => { if (props.active) loadData() })
watch(() => props.active, (isActive) => { if (isActive && isEmpty) loadData() })

// 4. Report stats after data loads
function reportStats() {
  updateHeroStats([
    { value: count, label: '标签1' },
    { value: otherCount, label: '标签2' },
  ])
}
</script>
```

**关键点：**
- 数据加载、状态管理、对话框全部在子组件内部，不泄露到父组件
- 通过 `props.active` 感知是否激活，避免不可见时浪费请求
- 通过 `useHeroConsumer().reportStats()` 上报 Hero 统计数据
- 跨 tab 导航（如打开设计器、跳转详情）通过 `emit` 通知父组件

### 约束规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | **禁止 `loadAllData()`** | 禁止在 `onMounted` 中一次性加载所有 tab 数据 |
| 2 | **禁止裸 `v-show`** | 每个 tab 区块必须有 `v-if="isVisited('key')"` + `v-show="activeTab === 'key'"` |
| 3 | **禁止 `window.addEventListener('project-changed')`** | 统一改用 `resetOn` ref |
| 4 | **子组件禁止 `inject` 字符串 key** | 统一使用 `useHeroConsumer()`（见下一节） |
| 5 | **子 Tab 必须是独立组件** | 禁止在父 `index.vue` 内联写 tab 内容（模板、逻辑、样式）；每个 tab 抽成独立 `.vue` 文件放 `components/` 目录 |

### 已接入 APP

ITSM / OPSflow / CMDB / Monitor / IAM / Integration / Job-Platform（7 个 APP，55 个 Tab）

---

## 组件通信规范（`useHeroProvider` / `useHeroConsumer`）

当父页面 Hero 的 stats、搜索框、过滤栏需要由子 Tab 组件动态填充时，**必须**使用 Symbol-based `provide`/`inject`，通过配套 composable 封装。

### 架构

```
父页面 (app/index.vue)
  └─ useHeroProvider()           ← provide stats + Teleport DOM refs
        ├─ HERO_STATS_KEY        → reactive HeroStatItem[]
        ├─ HERO_FILTER_KEY       → Ref<HTMLElement | null>
        └─ HERO_SEARCH_KEY       → Ref<HTMLElement | null>

子组件 (app/components/XxxTab.vue)
  └─ useHeroConsumer()           ← inject stats + Teleport DOM refs
        ├─ reportStats(items)     → 写入 hero stats
        ├─ filterEl              → Teleport 过滤栏目标
        └─ searchEl              → Teleport 搜索框目标
```

### 父页面用法

```ts
// app/index.vue — 只调用一次
import { useHeroProvider } from '/@/composables/useHeroProvider'

const { stats: heroStats, searchRef: heroSearchRef, filterRef: heroFilterRef, updateStats } = useHeroProvider()
```

模板中放置 Teleport 接收槽位：
```html
<div class="app-hero-inner">
  <div class="app-hero-left">...</div>
  <div ref="heroSearchRef" class="app-hero-search" />   <!-- 子组件搜索框 Teleport 目标 -->
  <div class="app-hero-stats">
    <template v-for="(stat, i) in heroStats" :key="i">  <!-- 动态渲染 stats -->
      <div v-if="i > 0" class="app-stat-divider" />
      <div class="app-stat-item">
        <span class="app-stat-value">{{ stat.value }}</span>
        <span class="app-stat-label">{{ stat.label }}</span>
      </div>
    </template>
  </div>
</div>
<div ref="heroFilterRef" class="app-hero-filter" />   <!-- 子组件过滤栏 Teleport 目标 -->
```

### 子组件用法

```ts
// app/components/XxxTab.vue
import { useHeroConsumer } from '/@/composables/useHeroConsumer'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const { searchEl, filterEl, reportStats: updateHeroStats } = useHeroConsumer()

// 本地包装函数，组件内部调用此函数来报告 stats
function reportStats() {
  updateHeroStats([
    { value: data.value.length, label: '总数' },
    { value: activeCount.value, label: '活跃' },
  ])
}

// 数据加载后报告 + active 变化时重新报告
watch(() => props.active, (isActive) => {
  if (isActive && data.value.length > 0) reportStats()
})
```

模板中 Teleport 到父页面：
```html
<Teleport v-if="active && searchEl" :to="searchEl">
  <el-input v-model="searchQuery" :placeholder="..." class="my-search-input" />
</Teleport>
```

### 约束规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | **禁止字符串 key** | 禁止 `provide('updateHeroStats', ...)` / `inject('updateHeroStats', ...)`，必须用 Symbol-based composable |
| 2 | **Teleport 必须加 `active` 守卫** | `v-if="active && searchEl"` — 防止多个 Tab 的 Teleport 内容同时写入同一 DOM 节点 |
| 3 | **子组件必须设 safe fallback** | `useHeroConsumer()` 内部 inject 带默认值 `null`，确保子组件独立渲染不崩溃 |
| 4 | **stats 必须 reactive** | `useHeroProvider` 内部用 `reactive([])` ，子组件通过 `reportStats()` 替换内容 |
| 5 | **不为空时才渲染** | 父页面 hero-filter 使用 `:not(:empty)` 条件 padding |

### 已接入 APP

ITSM（ServiceMarket + ServiceAdmin 搜索框 Teleport）、OPSflow（Project + Execution 搜索框 + 过滤栏 Teleport + 全部 8 个子组件 stats 上报）

---

## Vue 组件结构规范

所有 `.vue` 文件**必须**遵循以下三段式结构：

```vue
<template>
  <!-- 模板内容 -->
</template>

<script setup lang="ts" name="componentName">
// 脚本内容
</script>

<style scoped lang="scss">
// 样式内容
</style>
```

**规则：**

| # | 规则 | 说明 |
|---|------|------|
| 1 | **三段式顺序** | `<template>` → `<script setup>` → `<style scoped>`，禁止调换 |
| 2 | **name 属性** | `<script setup name="xxx">` 必须写 name，PascalCase（如 `DeptTreeCom`） |
| 3 | **script setup 优先** | 禁止使用 Options API（`export default { ... }`），统一 Composition API |
| 4 | **scoped 样式** | `<style>` 必须加 `scoped`，除非是全局覆写 |
| 5 | **lang="scss"** | 所有 `<style>` 使用 SCSS，禁止原始 CSS |
| 6 | **私有 class** | 组件内样式 class 以组件缩写为前缀（如 `.dtc-wrap`、`.msg-toolbar`），避免全局污染 |

**关于 `shallowRef` 和 `markRaw`：**
- 图标组件对象（如 `User`、`Male`、`Tickets`）放入 reactive container 时，必须用 `markRaw()` 包裹，避免 Vue 对 Component 对象做深层响应式代理。
- 当 ref 的值只关心整体替换（不关心深层属性变化）时，优先用 `shallowRef` 替代 `ref` 提升性能。

---

## Frontend Comment Rules

**Comments explain "why", not "what".**

| # | Rule | ✅ Correct | ❌ Wrong |
|---|------|------------|----------|
| 1 | Write a one-line responsibility comment at the top of every component | `<!-- DeptTree: lazy-load, drag-and-drop sorting -->` | No comment |
| 2 | For non-obvious logic, explain "why" | `// Reset before fetch to avoid race condition` | `// Fetch list` |
| 3 | For complex API calls, document the expected behavior | `// Returns { code, data, total }, data may be null` | No comment |
| 4 | For signals/events/pub-sub, document the trigger condition | `// Fires on node completion, consumed by pipeline_builder` | `// Send signal` |
| 5 | No useless comments | — | `// Set variable`, `// Loop` |
| 6 | All comments MUST be in English | `// Validate user input before saving` | Chinese comments |
| 7 | CSS hacks must have a comment | `// Override el-table default padding` | Bare hack code |

**Key principle:** Good code tells you "what" — comments exist only for context, constraints, and reasoning that the code cannot express on its own.

---

## TypeScript 类型规范

**禁止滥用 `any`。** 所有跨组件/跨模块的数据接口必须定义明确类型。

| # | 规则 | 说明 |
|---|------|------|
| 1 | **Props 接口** | 组件 Props 必须在 `<script setup>` 上方用 `interface` 定义，配合 `defineProps<Props>()` 使用 |
| 2 | **API 响应类型** | 每个 api.ts 必须导出对应实体类型，禁止 inline 声明 `res.data as any` |
| 3 | **ref 泛型** | `ref()` 必须加泛型（如 `ref<UserRecord[]>([])`），禁止裸 `ref([])` 或 `ref<any[]>([])` |
| 4 | **computed 类型** | 复杂 computed 必须显式标注返回类型 |
| 5 | **emit 类型** | `defineEmits<{ (e: 'eventName', payload: Type): void }>()`，禁止不加类型 |
| 6 | **后端序列化器** | DRF Serializer 必须对应 `data`、`results` 等字段定义明确的 `serializers.py` 输出类型 |

---

## 国际化规范（i18n First）

**所有新页面、新组件、新对话框，从第一行代码开始就必须使用 i18n，禁止硬编码中文。**

| # | 规则 | 说明 |
|---|------|------|
| 1 | **先写翻译键** | 新建页面时，先同时改 `web/src/i18n/lang/en.ts` 和 `zh-cn.ts`，加 `xxxPage` 命名空间段 |
| 2 | **模板用 `$t()`** | `{{ $t('message.pageName.key') }}`，禁止裸中文 |
| 3 | **脚本用 `t()`** | `t('message.pageName.key')`，从 `useI18n()` 取实例 |
| 4 | **不用字典 label 代替翻译** | `statusDict` 的 `item.label` 不会随语言切换，直接用 `$t` |
| 5 | **所有消息走 i18n** | `ElMessage`、`ElMessageBox.confirm`、`successMessage` 全要走翻译 |
| 6 | **动态参数用插值** | `t('xxx', { name: row.name })`，翻译文件用 `{name}` 占位 |

**Code Review 检查三样：** ① 翻译段有无添加到 en.ts/zh-cn.ts ② 模板有无裸中文 ③ 脚本有无裸中文

**命名规范：** `message.<pageName>.<camelCaseKey>`，如 `message.rolePage.statTotal`。

---

## 按钮使用规范（Button Style Guide）

所有 `el-button` **必须**遵循以下规范，确保全系统视觉统一：

| 场景 | size | type | icon | 示例 |
|------|------|------|------|------|
| 页面级操作（新增/创建/发布/保存） | `default` | `primary` | **必须** | `<el-button type="primary" :icon="Plus">新增</el-button>` |
| 工具栏次要（刷新/重置/导出） | `default` | 缺省 | **必须** | `<el-button :icon="Refresh">刷新</el-button>` |
| 搜索/查询 | `default` | `primary` | 无 | `<el-button type="primary">搜索</el-button>` |
| 表格行内操作（编辑/删除/查看） | `small` | `text` | 无 | `<el-button text size="small">编辑</el-button>` |
| 弹窗底部按钮 | `default` | 取消→缺省, 确认→`primary` | 无 | `<el-button @click="...">取消</el-button>` + `<el-button type="primary">确定</el-button>` |
| 树/图表区小操作 | `small` | `text` + `circle` | **必须** | `<el-button text circle :icon="Plus" size="small" />` |

**Icon 自动映射规则：**

| 按钮文本关键词 | Icon |
|---|---|
| 新增/添加/Add/Create | `Plus` |
| 编辑/Edit/Modify | `Edit` |
| 删除/Delete/Remove | `Delete` |
| 保存/Save | `Check` |
| 刷新/Refresh/Sync | `Refresh` |
| 发布/Publish/Deploy | `Promotion` / `Upload` |
| 导出/Export | `Download` |
| 导入/Import | `Upload` |
| 重置/Reset/Clear | `Refresh` |
| 查看/View/Detail | 无（行内操作，用 `text` 即可） |

**禁止项：**
- 禁止在弹窗底部按钮上使用 `size="small"`
- 禁止在表格行内使用 `type="primary" link` → 统一用 `text`
- 禁止 `text` 与 `type="primary"` 同时使用 → 去掉 `type="primary"`
- 禁止搜索按钮带图标

---

## Pinia Store 规范

**哪些状态放 Store：** 只有**跨组件共享**或**跨路由持久**的数据才放 Pinia Store。组件私有状态保持 local `ref()`。

| # | 规则 | 说明 |
|---|------|------|
| 1 | **store 文件路径** | 全局共享的 store 放 `stores/modules/`（如 `stores/modules/dept.ts`），页面私有 store 放 `stores/`（如 `stores/messageCenter.ts`） |
| 2 | **命名** | store 文件名 + export 名统一：`messageCenter.ts` → `export const useMessageCenterStore` |
| 3 | **持久化** | 需要 localStorage 持久化的 store，使用 `pinia-persist` 插件，在 `state` 中声明持久化 key |
| 4 | **action vs function** | 简单的 API 调用+赋值直接在组件中用 `await fetchData()`，不要封装到 store action 里。只有**多组件共享的状态变更**才用 store action |
| 5 | **getter 简化** | 能用 `computed()` 实现的派生数据就不要写 store getter |

---

## Key Files

- `web/src/styles/_tokens.scss` — design tokens (`$g-*` 变量)
- `web/src/styles/_mixins.scss` — reusable mixins
- `web/src/styles/_components.scss` — reusable classes (`.g-*`)
- `web/src/styles/global.scss` — 唯一入口（forward 以上三个文件）
