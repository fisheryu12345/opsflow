# ITSM 表单设计器迁移至 form-create-designer 方案

**日期**: 2026-07-12
**状态**: 设计中
**决策**: 方案 A — 全量迁移，设计器 + 渲染器一步到位

---

## 1. 背景与动机

### 1.1 当前实现

ITSM 表单设计器完全自研，基于 `vuedraggable` + Element Plus 构建：

- **设计器**: `FormDesigner.vue` (417行) — 三栏布局（工具箱 / 画布 / 属性面板），支持拖拽
- **渲染器**: `ItsmFormRenderer/index.vue` + `ItsmFormField.vue` (203行) — 15 种字段类型
- **自定义业务字段**: 6 个（MEMBERS人员选择、FILE附件、RICHTEXT富文本、TABLE子表格、SECTION分组、DATE日期）
- **数据格式**: 自定义 `ItsmField` JSON 结构
- **后端存储**: `State.fields` JSONField + `Field` ORM 模型双通道

代码分布在 `web/src/views/apps/itsm/designer/` (设计器, ~2000行) 和 `web/src/components/ItsmFormRenderer/` (渲染器, ~800行)。

### 1.2 替换动机

**降低长期维护成本。** 自研表单设计器需要持续维护拖拽交互、属性面板、字段类型扩展、验证逻辑等通用能力，这些是社区成熟方案已有覆盖的。引入 form-create-designer (MIT, ~5900 stars, 活跃维护) 可减少约 60% 的自研代码量。

### 1.3 约束条件

- **无需向后兼容** — 可彻底切换数据格式，不保留 ItsmField 格式兼容
- **全部替换** — 设计器 + 渲染器一起替换
- **所有业务字段必须保留** — 6 个自定义字段在 fc designer 上重新实现
- **后端 API 端点不变** — `/api/itsm/states/sync/` 等保持不变

---

## 2. 方案对比

| 维度 | 方案 A (全量迁移) | 方案 B (渐进式) | 方案 C (重构降本) |
|---|---|---|---|
| 迁移风险 | 中 | 低 | 无 |
| 维护成本降低 | 高 (~60%) | 低 (增加适配层) | 中 (~20%) |
| 社区能力复用 | 完全 | 仅设计器 | 无 |
| 预估工时 | ~9.5 天 | ~5 天 + 后续 | ~5 天 |
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
  │   ├─ TagInput/TagSelect/...         + FcMembers/FcFile/FcRichtext/FcTable/FcSection 扩展
  │   └─ MembersField/FileField/...

共享层: ItsmFormRenderer/types.ts       共享层: fcExtensions.ts + 自定义组件注册
```

### 3.2 不改动的部分

- AntV X6 工作流画布 (`index.vue`, `useDesigner.ts`)
- NodeConfigPanel（仅改动按钮绑定方式）
- 后端 API 端点 (`/api/itsm/states/sync/` 等)
- Ticket 运行时流程 (`TicketDetail.vue` → `node_submit`)
- 预设系统 API
- 部署/版本快照机制 (`WorkflowVersion`)
- 后端表结构（`State.fields` JSONField 天然兼容）

### 3.3 新数据流

```
用户拖拽字段 → <fc-designer> 生成 Rule[] → emit('save', rules) → NodeConfigPanel
  → selectedNode.setData({ fields: rules }) → save workflow
  → POST /api/itsm/states/sync/ { fields: Rule[] } → State.fields JSONField
  → Ticket 填单 → <form-create :rule="fields" /> 渲染 → node_submit
```

---

## 4. 字段类型映射

### 4.1 内置字段（直接映射，9 个）

| ITSM 类型 | form-create type | 说明 |
|---|---|---|
| STRING | `input` | 单行文本 |
| TEXT | `input` + type=textarea | 多行文本 |
| INT | `number` | 整数 |
| DATE | `datePicker` | 日期 |
| DATETIME | `datePicker` + type=datetime | 日期时间 |
| SELECT | `select` | 下拉选择 |
| RADIO | `radio` | 单选 |
| CHECKBOX | `checkbox` | 复选框 |
| MULTISELECT | `select` + multiple | 多选 |
| CASCADE | `cascader` | 级联（内置已覆盖） |

### 4.2 自定义字段（需移植，6 个）

| ITSM 类型 | 自定义 type | 复杂度 | 实现方式 |
|---|---|---|---|
| MEMBERS | `ItsmMembers` | 中 | el-select + 远程搜索用户 API |
| FILE | `ItsmFile` | 中 | el-upload + formCreateInject token 注入 |
| RICHTEXT | `ItsmRichtext` | 中 | 富文本编辑器 + v-model |
| TABLE | `ItsmTable` | 高 | form-create group 子表单 或 el-table 内嵌 |
| SECTION | `ItsmSection` | 低 | 分组标题/分割线，`input: false` |
| DATE | 内置 `datePicker` | — | 直接使用内置组件 |

---

## 5. 数据格式转换

### 5.1 格式映射

```
ItsmField.key                    → Rule.field
ItsmField.name                   → Rule.title
ItsmField.type                   → Rule.type (内置名或自定义名)
ItsmField.required               → Rule.validate: [{ required: true }]
ItsmField.placeholder            → Rule.props.placeholder
ItsmField.layout                 → Rule.itsmLayout (自定义扩展字段)
ItsmField.default                → Rule.itsmDefault (自定义扩展字段)
ItsmField.choice                 → Rule.props.options (select/radio等)
ItsmField.show_conditions        → Rule.itsmShowCondition (自定义扩展字段)
ItsmField.preset_id              → Rule.itsmPresetId (自定义扩展字段)
ItsmField.sort_order             → (数组索引隐式表达)
```

### 5.2 ITSM 扩展字段说明

form-create 的 Rule 对象允许任意额外字段，以下为 ITSM 专用扩展：

| 扩展字段 | 用途 | 消费方 |
|---|---|---|
| `itsmLayout` | 列宽：COL_12 / COL_8 / COL_6 / COL_4 / COL_3 | 渲染器包装组件 |
| `itsmDefault` | 字段默认值 | 运行态初始化 |
| `itsmShowCondition` | 条件显隐：`{ field, value }` | parser 转为 control 规则 |
| `itsmPresetId` | 选项预设 ID | 设计器 props 面板 + preset 同步 |

### 5.3 示例：NORMAL 节点默认字段

**当前格式 (ItsmField):**
```json
[
  { "key": "title", "name": "标题", "type": "STRING", "required": true, "layout": "COL_12" },
  { "key": "description", "name": "描述", "type": "TEXT", "layout": "COL_12" },
  { "key": "category", "name": "分类", "type": "SELECT", "layout": "COL_6", "choice": [...] },
  { "key": "priority", "name": "优先级", "type": "SELECT", "layout": "COL_6", "choice": [...] },
  { "key": "attachment", "name": "附件", "type": "FILE", "layout": "COL_12" }
]
```

**目标格式 (Rule):**
```json
[
  { "type": "input", "field": "title", "title": "标题", "validate": [{ "required": true }], "itsmLayout": "COL_12" },
  { "type": "input", "field": "description", "title": "描述", "props": { "type": "textarea", "rows": 3 }, "itsmLayout": "COL_12" },
  { "type": "select", "field": "category", "title": "分类", "props": { "options": [...] }, "itsmLayout": "COL_6" },
  { "type": "select", "field": "priority", "title": "优先级", "props": { "options": [...] }, "itsmLayout": "COL_6" },
  { "type": "ItsmFile", "field": "attachment", "title": "附件", "itsmLayout": "COL_12" }
]
```

---

## 6. 自定义组件移植

### 6.1 注册模式

每个自定义字段遵循相同模式：

```
① 创建 Vue SFC 组件（兼容 modelValue / disabled / formCreateInject）
② FcDesigner.component('ItsmXxx', Component) 注册设计态 + 运行态
③ 定义 DragRule { name, label, menu, rule(), props() }
④ designer.addComponent(dragRule) 挂载到工具箱
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

当前 TABLE 仅为占位 div。建议用 form-create `group` 子表单实现：

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

或保持轻量实现：内嵌 el-table + 动态行编辑，不追求完整子表单能力。

---

## 7. 后端适配

### 7.1 存储层

`State.fields` 为 `JSONField`，无 schema 约束。直接存储 `Rule[]`，无需改表。

### 7.2 Field 模型处理

```
当前状态: Field ORM 模型 + State.fields JSON 双写
目标状态: State.fields JSON 唯一数据源，Field 模型标记 deprecated
```

- `Field` 模型保留只读，删除 `batch_update` 等写入端点
- `StateSerializer` 不变（`fields = '__all__'`，JSON 透传）
- `Workflow.create_version()`: 从 `State.fields` JSON 直接复制字段快照
- Preset 同步: `_sync_referencing_state_fields()` 遍历 `State.fields` 中的 `itsmPresetId`

### 7.3 不改动的后端文件

- `itsm/urls.py` — API 端点不变
- `itsm/views/workflow_views.py` — ViewSet 不变
- `itsm/views/ticket_views.py` — Ticket 流程不变
- `itsm/services/workflow_builder.py` — Pipeline 构建不变（只读 fields JSON）
- `itsm/pipeline_plugins/components.py` — 组件不变

---

## 8. 设计器 UI 精简

```ts
const designerConfig = {
  // 隐藏不需要的内置菜单组
  hiddenMenu: ['subform', 'chart', 'aide', 'template'],
  // 隐藏不需要的内置组件
  hiddenItem: ['switch', 'rate', 'slider', 'colorPicker', 'timePicker',
               'upload', 'image', 'tree', 'frame', 'editor', 'group'],
  // 功能开关
  showSaveBtn: false,
  showPrintBtn: false,
  showImportBtn: false,
  showTemplate: false,
  showDevice: false,
  showLanguage: false,
  showJsonPreview: false,
  showGridLine: false,
  showQuickLayout: false,
  showPreviewBtn: true,
  // 行为
  autoActive: true,
  checkFieldUnique: true,
  autoResetField: false,  // ITSM 使用语义化 field key
}
```

自定义菜单：
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
    { name: 'ItsmSection', label: '分组', icon: 'icon-divider' },
  ]},
]
```

---

## 9. 文件改动清单

### 9.1 新建文件（7 个）

| 文件 | 说明 |
|---|---|
| `web/src/views/apps/itsm/designer/FcFormDesigner.vue` | fc-designer 包装组件 |
| `web/src/views/apps/itsm/designer/fcExtensions.ts` | DragRule 定义 + 自定义组件注册 + config |
| `web/src/components/ItsmFormRenderer/fields/FcMembersField.vue` | MEMBERS 移植 |
| `web/src/components/ItsmFormRenderer/fields/FcFileField.vue` | FILE 移植 |
| `web/src/components/ItsmFormRenderer/fields/FcRichtextField.vue` | RICHTEXT 移植 |
| `web/src/components/ItsmFormRenderer/fields/FcTableField.vue` | TABLE 移植 |
| `web/src/components/ItsmFormRenderer/fields/FcSectionDivider.vue` | SECTION 移植 |

### 9.2 修改文件（10 个）

| 文件 | 改动 |
|---|---|
| `web/package.json` | 新增 `@form-create/designer` `@form-create/element-ui` 依赖 |
| `web/src/main.ts` | `app.use(formCreate)` `app.use(FcDesigner)` |
| `web/src/views/apps/itsm/designer/index.vue` | 对话框中替换 FormDesigner → FcFormDesigner |
| `web/src/views/apps/itsm/designer/NodeConfigPanel.vue` | 按钮事件调整 |
| `web/src/views/apps/itsm/designer/shapes.ts` | `DEFAULT_NODE_FIELDS` 改为 Rule 格式 |
| `web/src/components/ItsmFormRenderer/index.vue` | 内部改为 `<form-create>` 渲染 |
| `web/src/views/apps/itsm/ticket/TicketDetail.vue` | ItsmFormRenderer → `<form-create>` |
| `backend/itsm/models/workflow.py` | `create_version()` 从 State.fields 直接取 |
| `backend/itsm/serializers/workflow_serializers.py` | FieldSerializer deprecated |
| `backend/itsm/services/preset_service.py` | 适配 `itsmPresetId` |

### 9.3 删除/归档文件（5 个）

| 文件 | 原因 |
|---|---|
| `web/src/views/apps/itsm/designer/FormDesigner.vue` | FcFormDesigner 替代 |
| `web/src/components/ItsmFormRenderer/ItsmFormField.vue` | form-create 内置渲染 |
| `web/src/components/ItsmFormRenderer/types.ts` | ItsmField 不再需要 |
| `web/src/components/ItsmFormRenderer/fields/DateField.vue` | form-create 内置替代 |
| `web/src/components/RenderForm/tags/` | 确认无其他模块依赖后删除 |

### 9.4 预估工时: ~9.5 天

| 阶段 | 内容 | 估时 |
|---|---|---|
| 环境搭建 | 安装依赖 + main.ts 注册 + fc-designer 渲染验证 | 0.5 天 |
| FcFormDesigner | 包装组件 + config + 菜单精简 | 1 天 |
| 6 个自定义组件 | MEMBERS, FILE, RICHTEXT, TABLE, SECTION, CASCADE(内置) | 2 天 |
| DragRule 定义 | 6 个扩展 + 内置组件筛选 | 1 天 |
| NodeConfigPanel 对接 | 对话框集成 + 数据流调通 | 1 天 |
| 渲染器替换 | TicketDetail + 表单渲染 | 1 天 |
| 后端适配 | create_version + preset sync + Field deprecated | 1 天 |
| 测试 & 修复 | 全流程回归测试 + bug fix | 2 天 |

---

## 10. 关键风险与缓解

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| form-create API 版本变更 | 升级时需适配 | 锁定 `@form-create/designer@^3.2` 主版本 |
| TABLE 子表格复杂度超预期 | 工时超标 | 先轻量实现（el-table 内嵌），后续迭代增强 |
| 内置组件 props 行为差异 | 渲染效果不一致 | 逐字段对比测试，必要时用 parser 修正 |
| 预设系统接入不畅 | 选项加载失败 | `setGlobalData` + fetch 选项源方案已验证可行 |
| `control` 语法表达力不足 | show_conditions 无法等价实现 | 回退到渲染包装层手动过滤可见字段 |

---

## 11. 验证计划

### 11.1 设计态验证

1. 打开节点配置 → 点击"添加/编辑字段" → fc-designer 正常渲染
2. 从工具箱拖入内置字段（input, select, radio 等）→ 画布正确渲染
3. 拖入自定义字段（ItsmMembers, ItsmFile 等）→ 自定义组件正常显示
4. 选中字段 → 右侧属性面板可编辑
5. 修改列布局、预设选项 → 即时生效
6. 预览模式 → 表单正确渲染
7. 保存 → Rule[] 正确存入 State.fields
8. 再次打开 → 已保存字段正确回显

### 11.2 运行态验证

1. 创建 Ticket → 进入填单节点 → `<form-create>` 渲染表单
2. 所有字段类型可正常填写
3. MEMBERS 可搜索用户
4. FILE 可上传附件
5. 条件显隐生效（选择 A → 显示字段 B）
6. 必填验证生效
7. 提交 → 表单数据正确发送到后端

### 11.3 部署验证

1. Workflow 部署 → WorkflowVersion 正确保存 Rule[]
2. 从版本创建 Ticket → 表单数据完整
3. 版本回滚 → 表单配置正确恢复

### 11.4 回归验证

1. 现有 Workflow 模板可加载（NodeConfigPanel、EdgeConfigPanel 不受影响）
2. Trigger 配置保存/加载正常
3. SLA 策略不受影响
4. 预设管理（Preset CRUD）功能正常

---

## 12. 参考

- [form-create 文档](https://form-create.com)
- [fc-designer GitHub](https://github.com/xaboy/form-create-designer)
- [FcDesigner使用助手](../../../.claude/skills/FcDesigner使用助手/AGENTS.md)
- [FcDesigner二开助手](../../../.claude/skills/FcDesigner二开助手/AGENTS.md)
- 现有实现: [FormDesigner.vue](../../../web/src/views/apps/itsm/designer/FormDesigner.vue)
- 现有渲染器: [ItsmFormRenderer](../../../web/src/components/ItsmFormRenderer/)
