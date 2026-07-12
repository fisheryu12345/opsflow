# ITSM 表单设计器迁移至 form-create-designer 方案

**日期**: 2026-07-12 (修订 v2)
**状态**: 设计中
**决策**: 方案 A — 全量迁移，设计器 + 渲染器一步到位

---

## 1. 背景与动机

### 1.1 当前实现

ITSM 表单设计器完全自研，基于 `vuedraggable` + Element Plus 构建：

- **设计器**: `FormDesigner.vue` (417行) — 三栏布局（工具箱 / 画布 / 属性面板），支持拖拽
- **渲染器**: `ItsmFormRenderer/index.vue` + `ItsmFormField.vue` (203行) — 15 种字段类型
- **自定义业务字段**: 7 个（MEMBERS人员选择、FILE附件、RICHTEXT富文本、TABLE子表格、CASCADE级联、SECTION分组、DATE日期）
  - 其中 CASCADE 使用 `TagCascader`（el-cascader 包装），选项来自 `attrs.options`/`attrs.api_endpoint`，不走标准 `choice` 数组
  - DATE 使用自定义 `DateField.vue`（`value-format="YYYY-MM-DD"`）
- **数据格式**: 自定义 `ItsmField` JSON 结构（key/name/type/required/layout/choice/default/placeholder/show_conditions/sort_order）
- **后端存储**: `State.fields` JSONField + `Field` ORM 模型双通道
- **运行态渲染消费者**: `TicketDetail.vue`、`ServiceDetail.vue`、`ServiceAdmin.vue`（3 个文件使用 ItsmFormRenderer）
- **现有验证**: 仅 `required` 布尔开关，无 async validation / pattern / min-max
- **条件显隐**: `show_conditions: { field, value }`（简单等价判断）
- **sort_order**: 渲染前按 `sort_order` 排序，不仅是设计态辅助

代码分布在 `web/src/views/apps/itsm/designer/` (设计器, ~2000行) 和 `web/src/components/ItsmFormRenderer/` (渲染器, ~800行)。

### 1.2 替换动机

**降低长期维护成本。** 自研表单设计器需要持续维护拖拽交互、属性面板、字段类型扩展、验证逻辑等通用能力，这些是社区成熟方案已有覆盖的。引入 form-create-designer (MIT, ~5900 stars, 活跃维护) 可减少约 60% 的自研代码量。

### 1.3 约束条件

- **无需向后兼容** — 可彻底切换数据格式，不保留 ItsmField 格式兼容
- **全部替换** — 设计器 + 渲染器一起替换
- **所有业务字段必须保留** — 7 个自定义字段在 fc designer 上重新实现
- **后端 API 端点不变** — `/api/itsm/states/sync/` 等保持不变
- **RenderForm/tags/ 不能删除** — OpsFlow `PropertyPanel.vue` 通过 `RenderForm.vue → FormItem.vue` 链路依赖全部 17 个 Tag 组件

---

## 2. 方案对比

| 维度 | 方案 A (全量迁移) | 方案 B (渐进式) | 方案 C (重构降本) |
|---|---|---|---|
| 迁移风险 | 中 | 低 | 无 |
| 维护成本降低 | 高 (~60%) | 低 (增加适配层) | 中 (~20%) |
| 社区能力复用 | 完全 | 仅设计器 | 无 |
| 预估工时 | ~10 天 | ~5 天 + 后续 | ~5 天 |
| 长期价值 | 高 | 中 | 低 |

**选择方案 A**，一步到位全量迁移。

---

## 3. 架构设计

### 3.1 替换范围

```
当前（自研）                              目标（form-create 生态）
─────────────────────────              ─────────────────────────
FormDesigner.vue                       <fc-designer>
  ├─ VueDraggable (工具箱)               ├─ 内置拖拽工具箱
  ├─ ItsmFormField (画布)                ├─ 内置画布渲染
  ├─ 属性面板 (手写 el-form)              ├─ 内置属性面板 + baseRule 扩展
  └─ 输出: ItsmField[]                   └─ 输出: form-create Rule[]

ItsmFormRenderer/index.vue             <form-create> 组件
  ├─ ItsmFormField.vue                  └─ 内置字段渲染器
  │   ├─ TagInput/TagSelect/...         + 7 个自定义扩展组件
  │   │   (from RenderForm/tags)        (FcMembers/FcFile/FcRichtext/
  │   └─ 自定义: MembersField,           FcTable/FcCascader/FcSection/FcDate)
  │       FileField, RichtextField,
  │       TableField, DateField,
  │       SectionDivider, TagCascader

共享层: types.ts (ItsmField)            共享层: fcExtensions.ts + 自定义组件注册
RenderForm/tags/ (保留不动)              RenderForm/tags/ (仍被 OpsFlow 使用)
```

### 3.2 不改动的部分

- AntV X6 工作流画布 (`index.vue`, `useDesigner.ts`)
- `NodeConfigPanel`（仅改动 `openFieldEditor` 事件绑定方式，事件签名不变）
- `useDesigner.ts` deep watcher（`fields` 在 `dirtyKeys` 中，watcher 不关心格式）
- 后端 API 端点（`/api/itsm/states/sync/`、`/api/itsm/presets/` 等不变）
- 预设系统 API
- `WorkflowVersion` 部署/版本快照机制
- 后端表结构（`State.fields` JSONField 天然兼容，不改 migration）
- `RenderForm/tags/` 目录（OpsFlow PropertyPanel 仍需要）

### 3.3 新数据流

```
用户拖拽字段 → <fc-designer> 生成 Rule[] → emit('save', rules) → NodeConfigPanel
  → designer.selectedNode.value.fields = rules → deep watcher sync to X6 cell
  → save workflow → POST /api/itsm/states/sync/ { fields: Rule[] }
  → State.fields JSONField → deploy → WorkflowVersion.fields (snapshot)
  → Ticket 填单 / ServiceDetail / ServiceAdmin → <form-create v-model="fillForm" :rule="fields" />
  → node_submit → fillForm data
```

### 3.4 渲染器 v-model 适配

当前 TicketDetail/ServiceDetail/ServiceAdmin 使用事件驱动模式：

```vue
<!-- 当前：事件驱动 -->
<ItsmFormRenderer
  :fields="node.fields"
  :data="fillForm"
  @field-change="(k, v) => fillForm[k] = v"
/>

<!-- 目标：v-model 双向绑定 -->
<form-create
  v-model="fillForm"
  :rule="node.fields"
  :option="formOption"
/>
```

### 3.5 submittedFieldLabels 适配

TicketDetail 当前从 `ItsmField.name` 构建标签映射：

```ts
// 当前
for (const f of (st.fields || [])) {
  labels[String(f.key)] = f.name || f.key
}

// 目标：从 Rule.title 取标签
for (const r of (st.fields || [])) {
  labels[r.field] = r.title || r.field
}
```

---

## 4. 字段类型映射

### 4.1 内置字段（直接映射，8 个）

| ITSM 类型 | form-create type | 说明 |
|---|---|---|
| STRING | `input` | 单行文本 |
| TEXT | `input` + type=textarea | 多行文本 |
| INT | `number` | 整数 |
| DATE | `datePicker` | 日期（form-create 内置 datePicker 支持 `valueFormat: "YYYY-MM-DD"`） |
| DATETIME | `datePicker` + type=datetime | 日期时间 |
| SELECT | `select` | 下拉选择 |
| RADIO | `radio` | 单选 |
| CHECKBOX | `checkbox` | 复选框 |
| MULTISELECT | `select` + multiple | 多选 |

> **DATE 修正**: 当前有自定义 `DateField.vue`（`el-date-picker` + `value-format="YYYY-MM-DD"`），form-create 内置 `datePicker` 通过 props 配置 `valueFormat` 可直接替代。

### 4.2 自定义字段（需移植，7 个）

| ITSM 类型 | 自定义 type | 复杂度 | 说明 |
|---|---|---|---|
| MEMBERS | `ItsmMembers` | 中 | el-select + 远程搜索用户 API |
| FILE | `ItsmFile` | 中 | el-upload + formCreateInject token 注入 |
| RICHTEXT | `ItsmRichtext` | 中 | 富文本编辑器 + v-model |
| TABLE | `ItsmTable` | 高 | 子表格（参考 6.4） |
| CASCADE | `ItsmCascader` | 中 | el-cascader 包装，选项从 `props.options` 或远程 API 加载 |
| SECTION | `ItsmSection` | 低 | 分组标题/分割线，`input: false` |

> **CASCADE 修正**: 之前误认为 form-create 内置 cascader 可直接替代。实际 `TagCascader` 是 el-cascader 包装，选项格式为 `attrs.options`（嵌套），与 form-create cascader 的 `props.options` 语义不同。需作为自定义组件移植。

---

## 5. 数据格式转换

### 5.1 格式映射

```
ItsmField.key                    → Rule.field
ItsmField.name                   → Rule.title
ItsmField.type                   → Rule.type (内置名或自定义名)
ItsmField.required               → Rule.validate: [{ required: true, message: '...' }]
ItsmField.placeholder            → Rule.props.placeholder
ItsmField.layout                 → Rule.itsmLayout (自定义扩展字段)
ItsmField.default                → Rule.itsmDefault (自定义扩展字段)
ItsmField.choice                 → Rule.props.options (select/radio/checkbox等)
ItsmField.show_conditions        → Rule.itsmShowCondition (自定义扩展字段)
ItsmField.preset_id              → Rule.itsmPresetId (自定义扩展字段)
ItsmField.sort_order             → Rule.itsmSortOrder (自定义扩展字段，显式保留)
```

> **sort_order 修正**: 原设计依赖数组索引隐式表达顺序。但 `ItsmFormRenderer` 渲染前主动按 `sort_order` 排序，不保证数组顺序与渲染顺序一致。改为在 Rule 上显式保留 `itsmSortOrder` 字段，渲染器包装组件按该字段排序。

### 5.2 ITSM 扩展字段说明

form-create 的 Rule 对象允许任意额外字段，以下为 ITSM 专用扩展：

| 扩展字段 | 用途 | 消费方 |
|---|---|---|
| `itsmLayout` | 列宽：COL_12 / COL_8 / COL_6 / COL_4 / COL_3 | 渲染器包装组件 |
| `itsmDefault` | 字段默认值 | 运行态 formData 初始化 |
| `itsmShowCondition` | 条件显隐：`{ field, value }` | parser 或 wrapper 转为 control / v-show |
| `itsmPresetId` | 选项预设 ID | 设计器 props 面板 + backend preset sync |
| `itsmSortOrder` | 显示顺序 | 渲染器包装组件排序 |

### 5.3 示例：NORMAL 节点默认字段

**当前格式 (ItsmField):**
```json
[
  { "key": "title", "name": "工单标题", "type": "STRING", "required": true, "layout": "COL_12", "placeholder": "如 服务器磁盘空间不足" },
  { "key": "description", "name": "详细描述", "type": "TEXT", "required": true, "layout": "COL_12", "placeholder": "请描述问题或需求详情" },
  { "key": "category", "name": "服务分类", "type": "SELECT", "required": true, "layout": "COL_6", "choice": [...] },
  { "key": "priority", "name": "优先级", "type": "SELECT", "required": true, "layout": "COL_6", "choice": [...] },
  { "key": "attachment", "name": "附件", "type": "FILE", "required": false, "layout": "COL_12" }
]
```

**目标格式 (Rule):**
```json
[
  { "type": "input", "field": "title", "title": "工单标题", "validate": [{ "required": true }], "itsmLayout": "COL_12", "itsmSortOrder": 0, "props": { "placeholder": "如 服务器磁盘空间不足" } },
  { "type": "input", "field": "description", "title": "详细描述", "validate": [{ "required": true }], "itsmLayout": "COL_12", "itsmSortOrder": 1, "props": { "type": "textarea", "rows": 3, "placeholder": "请描述问题或需求详情" } },
  { "type": "select", "field": "category", "title": "服务分类", "validate": [{ "required": true }], "itsmLayout": "COL_6", "itsmSortOrder": 2, "props": { "options": [{"label":"网络故障","value":"network"},...] } },
  { "type": "select", "field": "priority", "title": "优先级", "validate": [{ "required": true }], "itsmLayout": "COL_6", "itsmSortOrder": 3, "props": { "options": [{"label":"P1 危急","value":"P1"},...] } },
  { "type": "ItsmFile", "field": "attachment", "title": "附件", "itsmLayout": "COL_12", "itsmSortOrder": 4 }
]
```

---

## 6. 自定义组件移植

### 6.1 注册模式

每个自定义字段遵循相同模式：

```
① 创建 Vue SFC 组件（兼容 modelValue / disabled / formCreateInject）
② formCreate.component('ItsmXxx', Component) 注册运行态渲染
③ FcDesigner.component('ItsmXxx', Component) 注册设计态渲染
④ 定义 DragRule { name, label, menu, rule(), props() }
⑤ designer.addComponent(dragRule) 挂载到工具箱
```

### 6.2 MEMBERS 组件示例

```vue
<!-- FcMembersField.vue -->
<template>
  <el-select
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    multiple filterable remote
    :remote-method="searchUsers"
    :placeholder="formCreateInject?.props?.placeholder || '请选择人员'"
    :disabled="disabled"
  >
    <el-option v-for="u in users" :key="u.value" :label="u.label" :value="u.value" />
  </el-select>
</template>

<script setup lang="ts">
import { ref, inject } from 'vue'
const props = defineProps<{ modelValue?: any; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: any] }>()
const formCreateInject: any = inject('formCreateInject', {})
const users = ref<any[]>([])
async function searchUsers(query: string) {
  const res = await fetch(`/api/users/search/?q=${query}`).then(r => r.json())
  users.value = (res.data || []).map((u: any) => ({ label: u.username, value: u.id }))
}
</script>
```

### 6.3 DragRule 定义

```ts
// fcExtensions.ts
export const membersDragRule: DragRule = {
  name: 'ItsmMembers',
  label: '人员选择',
  icon: 'icon-user',
  menu: 'itsm',
  input: true,
  rule({ t }) {
    return {
      type: 'ItsmMembers',
      field: `members_${Date.now()}`,
      title: '人员选择',
      itsmLayout: 'COL_12',
      itsmSortOrder: 0,
      props: { placeholder: '请选择人员' },
    }
  },
  props() {
    return [
      { type: 'input', field: 'placeholder', title: '占位文字' },
      { type: 'switch', field: 'disabled', title: '禁用' },
    ]
  },
  validate: ['required'],
}
```

### 6.4 TABLE 组件策略

当前 TABLE 仅为占位 div（`TableField.vue` 中是一个 `dashed-border placeholder`）。建议用 form-create `group` 子表单实现：

```json
{
  "type": "group",
  "field": "sub_items",
  "title": "子表格",
  "props": {
    "formCreateRule": [
      { "type": "input", "field": "item_name", "title": "名称" },
      { "type": "number", "field": "item_count", "title": "数量" }
    ]
  }
}
```

备选方案：内嵌 el-table + 动态行编辑，不追求完整子表单能力。

### 6.5 CASCADE 移植要点

当前 `TagCascader` 特点：
- 选项来自 `attrs.options`（静态树形数据）或 `attrs.api_endpoint`（远程加载）
- 默认 `cascaderProps = { multiple: false, checkStrictly: true, emitPath: true }`
- 选项值格式为 `{ value, label, children? }` 嵌套结构

移植为 `ItsmCascader` DragRule 时：
- `props()` 面板暴露 `options`（静态）和 `api`（远程源）两种数据源切换
- 运行时组件包装 `el-cascader`，兼容嵌套选项格式

---

## 7. 后端适配

### 7.1 存储层

`State.fields` 为 `JSONField`，无 schema 约束。直接存储 `Rule[]`，无需改表、无需 migration。

### 7.2 Field 模型处理

```
当前状态: Field ORM 模型 + State.fields JSON 双写
目标状态: State.fields JSON 唯一数据源，Field 模型标记 deprecated
```

具体改动：

| 后端文件 | 当前行为 | 目标行为 |
|---|---|---|
| `models/workflow.py:create_version()` | 读 `s.field_defs.all()` 遍历 Field ORM，逐字段 snapshot 到 WorkflowVersion.fields | 直接从 `s.fields` JSONField 复制，不改动 |
| `views/workflow_views.py:rollback()` | `Field.objects.filter(...).delete()` + `Field.objects.create(...)` 重建 Field 行 | 改为将版本 JSON 写回 `State.fields`，不操作 Field 表 |
| `views/workflow_views.py:FieldViewSet` | CRUD + `batch_update` 端点 | 保留端点路径不变，内部改为读写 `State.fields` JSON |
| `serializers/workflow_serializers.py:FieldSerializer` | `fields = '__all__'` | 标记 deprecated，新增注释说明 |
| `serializers/preset.py:_sync_referencing_fields()` | `Field.objects.filter(preset=preset).update(choice=...)` | 改为遍历 `State.fields` JSON 中的 `itsmPresetId` |
| `serializers/preset.py:_sync_referencing_state_fields()` | 遍历 `State.fields` JSON（已有逻辑） | 适配 `itsmPresetId` 字段名 |

### 7.3 冗余字段处理

| 后端字段 | 状态 | 处理 |
|---|---|---|
| `Field.validate_type` | 冗余（`Field.required` 已表达同一语义，无 server-side 逻辑消费） | 不再写入，读取时忽略 |
| `Field.source_type` | 死代码（API 选项零实现，仅 snapshot 传递） | 不再写入，读取时忽略 |
| `Field.meta` | pass-through（仅 snapshot 到 WorkflowVersion，backend 不解析） | Rule 原生支持任意扩展字段，不需要独立的 meta 容器 |

### 7.4 不改动的后端文件

- `itsm/urls.py` — API 端点不变
- `itsm/views/ticket_views.py` — Ticket 流程不变
- `itsm/services/workflow_builder.py` — Pipeline 构建不变（只读 fields JSON）
- `itsm/pipeline_plugins/components.py` — 组件不变

---

## 8. 设计器 UI 精简

```ts
const designerConfig = {
  // 隐藏不需要的内置菜单组
  hiddenMenu: ['subform', 'chart', 'aide', 'template'],
  // 隐藏不需要的内置组件（保留 input/textarea/number/datePicker/select/radio/checkbox/cascader）
  hiddenItem: ['switch', 'rate', 'slider', 'colorPicker', 'timePicker',
               'upload', 'image', 'tree', 'frame', 'editor', 'group'],
  // 功能开关
  showSaveBtn: false,         // ITSM 对话框自行管理保存
  showPrintBtn: false,
  showImportBtn: false,
  showTemplate: false,
  showDevice: false,
  showLanguage: false,
  showJsonPreview: false,
  showGridLine: false,
  showQuickLayout: false,
  showPreviewBtn: true,       // 保留预览
  // 行为
  autoActive: true,
  checkFieldUnique: true,
  autoResetField: false,      // ITSM 使用语义化 field key，不自动重置
  autoResetName: false,
}
```

自定义菜单（覆盖默认左侧工具箱）：
```ts
const customMenu = [
  { name: 'main', title: '基础字段', list: [
    { name: 'input', label: '单行文本', icon: 'icon-input' },
    { name: 'textarea', label: '多行文本', icon: 'icon-textarea' },
    { name: 'number', label: '整数', icon: 'icon-number' },
    { name: 'datePicker', label: '日期', icon: 'icon-date' },
    { name: 'select', label: '下拉选择', icon: 'icon-select' },
    { name: 'radio', label: '单选', icon: 'icon-radio' },
    { name: 'checkbox', label: '复选框', icon: 'icon-checkbox' },
  ]},
  { name: 'itsm', title: '业务字段', list: [
    { name: 'ItsmMembers', label: '人员选择', icon: 'icon-user' },
    { name: 'ItsmFile', label: '附件', icon: 'icon-upload' },
    { name: 'ItsmRichtext', label: '富文本', icon: 'icon-editor' },
    { name: 'ItsmTable', label: '子表格', icon: 'icon-table' },
    { name: 'ItsmCascader', label: '级联', icon: 'icon-cascader' },
    { name: 'ItsmSection', label: '分组', icon: 'icon-divider' },
  ]},
]
```

> **注意**: cascader 被加入 `hiddenItem`，因为我们提供自定义 `ItsmCascader` 覆盖，不需要内置版本出现在工具箱中。

### 8.1 右侧面板 ITSM 扩展配置

通过 `baseRule` 追加 ITSM 专属配置项：

```ts
const config = {
  appendConfigData: ['itsmLayout', 'itsmShowCondition', 'itsmPresetId'],
  baseRule: {
    append: true,
    rule({ t }) {
      return [
        // 列布局
        {
          type: 'radio',
          field: 'itsmLayout',
          title: '列宽',
          value: 'COL_12',
          options: [
            { label: '整行', value: 'COL_12' },
            { label: '2/3',  value: 'COL_8' },
            { label: '半行', value: 'COL_6' },
            { label: '1/3',  value: 'COL_4' },
            { label: '1/4',  value: 'COL_3' },
          ],
        },
        // 条件显隐开关
        { type: 'switch', field: 'itsmShowConditionEnabled', title: '条件显隐' },
      ]
    }
  },
}
```

---

## 9. 文件改动清单

### 9.1 新建文件（8 个）

| 文件 | 说明 |
|---|---|
| `web/src/views/apps/itsm/designer/FcFormDesigner.vue` | fc-designer 包装组件（setRule/getRule、保存/取消） |
| `web/src/views/apps/itsm/designer/fcExtensions.ts` | 7 个 DragRule + config + 自定义组件注册 + hiddenMenu/hiddenItem |
| `web/src/components/ItsmFormRenderer/fields/FcMembersField.vue` | MEMBERS 移植（el-select + 远程用户搜索） |
| `web/src/components/ItsmFormRenderer/fields/FcFileField.vue` | FILE 移植（el-upload + token 注入） |
| `web/src/components/ItsmFormRenderer/fields/FcRichtextField.vue` | RICHTEXT 移植（富文本编辑器 + v-model） |
| `web/src/components/ItsmFormRenderer/fields/FcTableField.vue` | TABLE 移植（group 子表单 / el-table 内嵌） |
| `web/src/components/ItsmFormRenderer/fields/FcCascaderField.vue` | CASCADE 移植（el-cascader + 选项源适配） |
| `web/src/components/ItsmFormRenderer/fields/FcSectionDivider.vue` | SECTION 移植（分组标题/分割线） |

### 9.2 修改文件（13 个前端 + 6 个后端）

**前端：**

| 文件 | 改动 |
|---|---|
| `web/package.json` | 新增 `@form-create/designer@^3` `@form-create/element-ui@^3` |
| `web/src/main.ts` | `app.use(formCreate)` + `app.use(FcDesigner)` + CSS 导入 |
| `web/src/views/apps/itsm/designer/index.vue` | 对话框替换 FormDesigner → FcFormDesigner |
| `web/src/views/apps/itsm/designer/shapes.ts` | `DEFAULT_NODE_FIELDS` 从 ItsmField 格式改为 Rule 格式 |
| `web/src/components/ItsmFormRenderer/index.vue` | 内部改为 `<form-create>` 渲染，保留 mode/fields/data 接口 |
| `web/src/views/apps/itsm/TicketDetail.vue` | `ItsmFormRenderer` → `<form-create v-model>`；`@field-change` 移除；`submittedFieldLabels` 改用 `rule.title` |
| `web/src/views/apps/itsm/catalog/ServiceDetail.vue` | 同 TicketDetail：`ItsmFormRenderer` → `<form-create>` |
| `web/src/views/apps/itsm/catalog/ServiceAdmin.vue` | 同 TicketDetail：`ItsmFormRenderer` → `<form-create>` |
| `web/src/views/apps/itsm/designer/ValidateDialog.vue` | 如验证逻辑引用字段格式，适配 Rule 格式 |
| `web/src/i18n/pages/itsm/zh-cn.ts` | 新增 fc-designer 相关 i18n 键（如菜单标签） |
| `web/src/i18n/pages/itsm/en.ts` | 同上英文翻译 |

**后端：**

| 文件 | 改动 |
|---|---|
| `backend/itsm/models/workflow.py` | `create_version()`: 改为从 `State.fields` JSON 直接复制字段 |
| `backend/itsm/views/workflow_views.py` | `rollback()`: 改为写回 `State.fields`；`batch_update`: 改为操作 State.fields JSON |
| `backend/itsm/serializers/workflow_serializers.py` | `FieldSerializer`: 标记 deprecated |
| `backend/itsm/serializers/preset.py` | `_sync_referencing_fields()`: 适配 `itsmPresetId` 字段名 |
| `backend/itsm/services/preset_service.py` | 同上 preset 同步逻辑 |
| `backend/itsm/migrations/` | 新增 migration: 移除 `Field` 表（可选，或只标记 deprecated 不删表） |

### 9.3 删除文件（4 个）

| 文件 | 原因 | 注意 |
|---|---|---|
| `web/src/views/apps/itsm/designer/FormDesigner.vue` | 被 FcFormDesigner 替代 | — |
| `web/src/components/ItsmFormRenderer/ItsmFormField.vue` | form-create 内置渲染替代 | — |
| `web/src/components/ItsmFormRenderer/types.ts` | ItsmField 类型不再需要 | — |
| `web/src/components/ItsmFormRenderer/fields/DateField.vue` | form-create 内置 datePicker 替代 | `value-format="YYYY-MM-DD"` 通过 props 配置 |

> **RenderForm/tags/ 保留不动**（OpsFlow PropertyPanel 依赖）。

### 9.4 预估工时: ~10 天

| 阶段 | 内容 | 估时 |
|---|---|---|
| 环境搭建 | 安装依赖 + main.ts 注册 + fc-designer 渲染验证 | 0.5 天 |
| FcFormDesigner | 包装组件 + config + 菜单精简 + baseRule 扩展 | 1 天 |
| 7 个自定义组件 | MEMBERS, FILE, RICHTEXT, TABLE, CASCADE, SECTION, DATE(已内置) | 2.5 天 |
| DragRule 定义 | 7 个扩展 + 内置组件筛选 + 注册脚本 | 1 天 |
| 设计器集成 | NodeConfigPanel 对接 + index.vue 对话框替换 + 数据流 | 0.5 天 |
| 渲染器替换 | TicketDetail + ServiceDetail + ServiceAdmin 的 v-model 适配 | 1 天 |
| 后端适配 | create_version + rollback + Field deprecated + preset sync | 1.5 天 |
| 测试 & 修复 | 全流程回归测试（设计态 + 运行态 + 部署） + bug fix | 2 天 |

---

## 10. 关键风险与缓解

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| form-create API 版本变更 | 升级时需适配 | 锁定 `@form-create/designer@^3.2` 主版本 |
| TABLE 子表格复杂度超预期 | 工时超标 | 先轻量实现（el-table 内嵌），`group` 子表单作为后续迭代 |
| CASCADE 选项格式不兼容 | 静态/远程数据源切换不工作 | 提供两种 DragRule 变体或统一为 `props.options` + `props.api` 双模式 |
| `control` 语法表达力不足 | show_conditions 无法等价实现 | 回退到渲染包装层手动 `v-show` 过滤，不依赖 control |
| 预设系统接入不畅 | 选项加载失败 | `setGlobalData` + fetch 选项源方案；fallback 为静态选项 |
| ServiceDetail/ServiceAdmin 遗漏 | 渲染器替换不完整 | 已在修改清单中明确列出 |

---

## 11. 验证计划

### 11.1 设计态验证

1. 打开节点配置 → 点击"添加/编辑字段" → fc-designer 正常渲染
2. 从工具箱拖入内置字段（input, select, radio 等）→ 画布正确渲染
3. 拖入自定义字段（ItsmMembers, ItsmFile, ItsmCascader 等）→ 自定义组件正常显示
4. 选中字段 → 右侧属性面板可编辑（包括 itsmLayout、条件显隐等 ITSM 扩展）
5. 修改列布局、预设选项 → 即时生效
6. 预览模式 → 表单正确渲染
7. 保存 → Rule[] 正确存入 State.fields
8. 再次打开 → 已保存字段正确回显（setRule 还原）

### 11.2 运行态验证

1. 创建 Ticket → 进入填单节点 → `<form-create>` 渲染表单
2. 所有字段类型可正常填写（内置 + 自定义共 15 种）
3. MEMBERS 可搜索用户
4. FILE 可上传附件
5. CASCADE 可展开级联选择
6. 条件显隐生效（选择 A → 显示字段 B）
7. 必填验证生效
8. 提交 → formData 正确发送到后端 `node_submit`

### 11.3 服务目录验证

1. ServiceDetail.vue → 服务预览页表单正常渲染
2. ServiceAdmin.vue → 服务管理页 `form_fields` 预览正常

### 11.4 部署验证

1. Workflow 部署 → WorkflowVersion 正确保存 Rule[]
2. 从版本创建 Ticket → 表单数据完整
3. 版本回滚 → State.fields 正确恢复（Rollback 写回 JSON）

### 11.5 回归验证

1. 现有 Workflow 模板可加载（NodeConfigPanel、EdgeConfigPanel 不受影响）
2. Trigger 配置保存/加载正常
3. SLA 策略不受影响
4. 预设管理（Preset CRUD）功能正常
5. OpsFlow PropertyPanel 正常（RenderForm/tags 未删除）

---

## 12. 设计审查修正记录 (v2)

| # | 问题 | 修正 |
|---|---|---|
| 1 | 误判 RenderForm/tags/ 可删除 | OpsFlow PropertyPanel 通过 `RenderForm.vue → FormItem.vue` 链依赖全部 17 个 Tag。保留不动。 |
| 2 | 误判 CASCADE 可用内置 cascader | `TagCascader` 选项格式为 `attrs.options`，与 form-create 不同。改为自定义 ItsmCascader 移植。 |
| 3 | 遗漏 ServiceDetail/ServiceAdmin | TicketDetail 不是唯一渲染器消费者。新增 2 个文件到修改清单。 |
| 4 | 事件驱动 vs v-model 不兼容 | `@field-change` 改为 `v-model` 双向绑定。修改 TicketDetail/ServiceDetail/ServiceAdmin 三处。 |
| 5 | sort_order 不是纯设计态 | `ItsmFormRenderer` 渲染前主动排序。Rule 上显式保留 `itsmSortOrder` 扩展字段。 |
| 6 | submittedFieldLabels 构建方式 | `f.name` → `r.title` 适配。 |
| 7 | create_version() 读 Field ORM | 改为读 `State.fields` JSONField 直接复制。 |
| 8 | rollback() 重建 Field 行 | 改为写回 `State.fields` JSON。 |
| 9 | validate_type/source_type/meta 冗余字段 | 明确处理策略：不再写入，读取忽略。 |
| 10 | 前端 Field API 调用路径 | 确认 `fieldApi` 通过 `StateSync` 间接调用 `/api/itsm/states/sync/`，FieldViewSet 的 CRUD 端点保留不变。 |

---

## 13. 参考

- [form-create 文档](https://form-create.com)
- [fc-designer GitHub](https://github.com/xaboy/form-create-designer)
- [FcDesigner使用助手](../../../.claude/skills/FcDesigner使用助手/AGENTS.md) — 实例 API、config、DragRule、事件、Element/Antd 差异
- [FcDesigner使用助手 types.md](../../../.claude/skills/FcDesigner使用助手/references/types.md) — TypeScript 类型权威口径
- [FcDesigner二开助手](../../../.claude/skills/FcDesigner二开助手/AGENTS.md) — 源码分层、DragRule 定制、属性处理器、覆盖渲染器
- 现有实现: [FormDesigner.vue](../../../web/src/views/apps/itsm/designer/FormDesigner.vue)
- 现有渲染器: [ItsmFormRenderer](../../../web/src/components/ItsmFormRenderer/)