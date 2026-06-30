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
| 5 | **已对齐页面** | portal / opsflow / opsflow-dashboard / itsm / integration / cmdb / job-platform / iam / opsflow-log / opsflow-knowledge / opsflow-approval / opsflow-webhook / opsflow-template / open-api |

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

## 前端注释规范

**注释是解释"为什么"，不是"是什么"。**

| # | 规则 | ✅ 正确示例 | ❌ 错误示例 |
|---|------|------------|------------|
| 1 | 组件顶部写一句话职责说明 | `<!-- 部门树组件：懒加载、拖拽排序 -->` | 不写注释 |
| 2 | 非自明的逻辑写"为什么" | `// 先重置再 fetch，避免竞态` | `// 获取列表` |
| 3 | 复杂 API 调用写预期行为 | `// 返回 { code, data, total }，data 可能为 null` | 不写注释 |
| 4 | 信号/事件/发布订阅写触发条件 | `// 节点完成时触发，pipeline_builder 监听此信号` | `// 发送信号` |
| 5 | 禁止废话注释 | — | `// 设置变量`、`// 循环` |
| 6 | 中英双语可选 | 复杂的业务逻辑用中文，纯技术说明用英文 | — |
| 7 | CSS hack 必须注释 | `// 覆盖 el-table 默认内边距` | 裸 hack 代码 |

**关键原则：** 好的代码本身就能说明"是什么"——注释的唯一价值是解释代码无法表达的上下文、约束和缘由。

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
