# 实施计划：ITSM 表单设计器迁移至 form-create-designer

**关联设计文档**: `2026-07-12-itsm-fc-designer-migration-design.md`
**总估时**: ~10 天
**前置条件**: 设计文档已审批通过

---

## Phase 1: 环境搭建 (0.5 天)

### Task 1.1: 安装依赖

**文件**: `web/package.json`

```bash
cd web
npm install @form-create/designer@^3 @form-create/element-ui@^3
```

**验证**: `npm list @form-create/designer @form-create/element-ui` 显示版本号

---

### Task 1.2: 注册到 main.ts

**文件**: `web/src/main.ts`

在现有 `app.use(...)` 调用之后追加：

```ts
// form-create ecosystem (ITSM form designer migration)
import formCreate from '@form-create/element-ui'
import FcDesigner from '@form-create/designer'
import '@form-create/element-ui/dist/form-create.min.css'
import '@form-create/designer/dist/index.css'

app.use(formCreate)
app.use(FcDesigner)
```

**验证**: `npm run dev` 启动无报错，浏览器 console 无 `formCreate is not defined`

---

## Phase 2: 自定义组件与扩展 (3.5 天)

### Task 2.1: 创建 fcExtensions.ts（配置中枢）

**新建文件**: `web/src/views/apps/itsm/designer/fcExtensions.ts`

此文件是全部配置的单一入口，包含：
- `designerConfig` — 精简后的 config 对象
- `customMenu` — 自定义工具箱菜单
- 7 个 `DragRule` 定义
- `registerCustomComponents(designer)` — 入口函数

```ts
// fcExtensions.ts
import type { Config, DragRule, Menu } from '@form-create/designer'
import FcDesigner from '@form-create/designer'
import formCreate from '@form-create/element-ui'
import FcMembersField from '/@/components/ItsmFormRenderer/fields/FcMembersField.vue'
import FcFileField from '/@/components/ItsmFormRenderer/fields/FcFileField.vue'
import FcRichtextField from '/@/components/ItsmFormRenderer/fields/FcRichtextField.vue'
import FcTableField from '/@/components/ItsmFormRenderer/fields/FcTableField.vue'
import FcCascaderField from '/@/components/ItsmFormRenderer/fields/FcCascaderField.vue'
import FcSectionDivider from '/@/components/ItsmFormRenderer/fields/FcSectionDivider.vue'

// ── Config ──
export const designerConfig: Config = {
  hiddenMenu: ['subform', 'chart', 'aide', 'template'],
  hiddenItem: ['switch', 'rate', 'slider', 'colorPicker', 'timePicker',
               'upload', 'image', 'tree', 'frame', 'editor', 'group', 'cascader'],
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
  autoActive: true,
  checkFieldUnique: true,
  autoResetField: false,
  autoResetName: false,
}

// ── Custom Menu ──
export const customMenu: Menu[] = [
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

// ── DragRule definitions (one per custom field — see Task 2.2-2.8) ──

export function registerCustomComponents(designer: any) {
  // Register runtime components
  formCreate.component('ItsmMembers', FcMembersField)
  formCreate.component('ItsmFile', FcFileField)
  formCreate.component('ItsmRichtext', FcRichtextField)
  formCreate.component('ItsmTable', FcTableField)
  formCreate.component('ItsmCascader', FcCascaderField)
  formCreate.component('ItsmSection', FcSectionDivider)

  // Register design-time components
  FcDesigner.component('ItsmMembers', FcMembersField)
  FcDesigner.component('ItsmFile', FcFileField)
  FcDesigner.component('ItsmRichtext', FcRichtextField)
  FcDesigner.component('ItsmTable', FcTableField)
  FcDesigner.component('ItsmCascader', FcCascaderField)
  FcDesigner.component('ItsmSection', FcSectionDivider)

  // Add menu and drag rules
  designer.addMenu({ name: 'itsm', title: '业务字段' })
  designer.addComponent([membersDR, fileDR, richtextDR, tableDR, cascaderDR, sectionDR])
}
```

**验证**: `npx vue-tsc --noEmit` 类型检查通过

---

### Task 2.2: FcSectionDivider（最简单，先打通流程）

**新建文件**: `web/src/components/ItsmFormRenderer/fields/FcSectionDivider.vue`

```vue
<template>
  <div class="fc-section">
    <div class="fc-section-line" />
    <span class="fc-section-label">{{ formCreateInject?.props?.label || '分组' }}</span>
    <div class="fc-section-line" />
  </div>
</template>

<script setup lang="ts">
import { inject } from 'vue'
const formCreateInject: any = inject('formCreateInject', {})
</script>

<style scoped>
.fc-section { display: flex; align-items: center; gap: 10px; margin: 12px 0; width: 100%; }
.fc-section-line { flex: 1; height: 1px; background: #e4e7ed; }
.fc-section-label { font-size: 13px; font-weight: 600; color: #606266; white-space: nowrap; }
</style>
```

在 `fcExtensions.ts` 中定义的 DragRule：
```ts
export const sectionDR: DragRule = {
  name: 'ItsmSection', label: '分组', icon: 'icon-divider',
  menu: 'itsm', input: false, mask: false,
  rule() { return { type: 'ItsmSection', title: '新分组', itsmLayout: 'COL_12', itsmSortOrder: 0 } },
  props() { return [{ type: 'input', field: 'title', title: '分组名称' }] },
}
```

**验证**: 拖入分组到画布，标签可编辑

---

### Task 2.3: FcMembersField（人员选择）

**新建文件**: `web/src/components/ItsmFormRenderer/fields/FcMembersField.vue`

复用现有 `MembersField.vue` 的业务逻辑，改写为 form-create 兼容格式：
- 注入 `formCreateInject` 获取 `props.placeholder` 和 `disabled`
- 使用 `modelValue` / `update:modelValue` 作为 v-model 契约
- 调用现有 `/api/users/search/` 端点

**DragRule** (在 fcExtensions.ts):
```ts
export const membersDR: DragRule = {
  name: 'ItsmMembers', label: '人员选择', icon: 'icon-user',
  menu: 'itsm', input: true,
  rule() { return { type: 'ItsmMembers', field: `members_${Date.now()}`, title: '人员选择', itsmLayout: 'COL_12', itsmSortOrder: 0, props: { placeholder: '请选择人员' } } },
  props() { return [
    { type: 'input', field: 'placeholder', title: '占位文字' },
    { type: 'switch', field: 'disabled', title: '禁用' },
    { type: 'switch', field: 'multiple', title: '多选', value: true },
  ]},
  validate: ['required'],
}
```

**验证**: 拖入画布 + 运行态可搜索用户

---

### Task 2.4: FcFileField（附件上传）

**新建文件**: `web/src/components/ItsmFormRenderer/fields/FcFileField.vue`

- 使用 `el-upload`，通过 `formCreateInject` 获取 token/API 地址
- 上传成功回调写回 `file.url`
- 实现 `modelValue` / `update:modelValue`

**验证**: 拖入画布 + 运行态可上传文件

---

### Task 2.5: FcRichtextField（富文本）

**新建文件**: `web/src/components/ItsmFormRenderer/fields/FcRichtextField.vue`

- 内嵌富文本编辑器（Quill 或 TinyMCE，视项目现有依赖）
- 如果项目无富文本编辑器依赖，先用 `el-input` textarea（当前实现也是如此）

**验证**: 拖入画布 + 运行态可输入多行文本

---

### Task 2.6: FcCascaderField（级联选择）

**新建文件**: `web/src/components/ItsmFormRenderer/fields/FcCascaderField.vue`

- 包装 `el-cascader`，支持静态 `props.options`（嵌套格式）和远程 `props.api` 两种数据源
- 默认 `cascaderProps = { multiple: false, checkStrictly: true, emitPath: true }`

**DragRule**:
```ts
export const cascaderDR: DragRule = {
  name: 'ItsmCascader', label: '级联', icon: 'icon-cascader',
  menu: 'itsm', input: true,
  rule() { return { type: 'ItsmCascader', field: `cascade_${Date.now()}`, title: '级联', itsmLayout: 'COL_12', itsmSortOrder: 0 } },
  props() { return [
    { type: 'input', field: 'placeholder', title: '占位文字' },
    { type: 'switch', field: 'disabled', title: '禁用' },
  ]},
  validate: ['required'],
}
```

**验证**: 拖入画布 + 运行态可展开级联选择

---

### Task 2.7: FcTableField（子表格）

**新建文件**: `web/src/components/ItsmFormRenderer/fields/FcTableField.vue`

先轻量实现：内嵌 `el-table` + 动态行增删。后续迭代升级为 form-create `group` 子表单。

**验证**: 拖入画布（显示占位预览）+ 运行态可编辑子表格行

---

### Task 2.8: DATE 字段（内置 datePicker 直接替代）

DATE 不需要新建自定义组件。form-create 内置 `datePicker` 通过 props 配置 `valueFormat: 'YYYY-MM-DD'` 可直接替代当前 `DateField.vue`。

在 DragRule 层面，datePicker 是内置组件，已包含在 `customMenu.main` 中。

**验证**: 拖入 datePicker 到画布，props 面板可配置 `valueFormat`

---

## Phase 3: 设计器集成 (1.5 天)

### Task 3.1: 创建 FcFormDesigner.vue

**新建文件**: `web/src/views/apps/itsm/designer/FcFormDesigner.vue`

```vue
<template>
  <div class="fc-itsm-wrap">
    <fc-designer
      ref="designerRef"
      :config="designerConfig"
      :menu="customMenu"
      height="560px"
    />
  </div>
  <div class="fc-itsm-footer">
    <el-button @click="$emit('cancel')">{{ $t('message.common.cancel') }}</el-button>
    <el-button type="primary" @click="handleConfirm">
      {{ $t('message.formDesigner.save') }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { designerConfig, customMenu, registerCustomComponents } from './fcExtensions'

const props = defineProps<{ fields?: any[] }>()
const emit = defineEmits<{ save: [fields: any[]]; cancel: [] }>()

const designerRef = ref()

onMounted(() => {
  registerCustomComponents(designerRef.value)
  // Load existing fields for editing
  if (props.fields?.length) {
    designerRef.value.setRule(props.fields)
  }
})

// Watch for external field changes (re-open dialog with new fields)
watch(() => props.fields, (f) => {
  if (f && designerRef.value) {
    designerRef.value.setRule(f)
  }
})

function handleConfirm() {
  const rules = designerRef.value.getRule()
  emit('save', rules)
}
</script>

<style scoped>
.fc-itsm-wrap { border: 1px solid #e4e7ed; border-radius: 6px; overflow: hidden; }
.fc-itsm-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 8px 12px; border-top: 1px solid #e4e7ed; background: #fafafa; }
</style>
```

**验证**: 在对话框中渲染 fc-designer，工具箱显示自定义菜单

---

### Task 3.2: 更新 designer/index.vue

**文件**: `web/src/views/apps/itsm/designer/index.vue`

改动点：
1. 将 `import FormDesigner from './FormDesigner.vue'` 改为 `import FcFormDesigner from './FcFormDesigner.vue'`
2. 将 `<FormDesigner :fields="editingFields" @save="onFieldsSave" @cancel="..." />` 改为 `<FcFormDesigner :fields="editingFields" @save="onFieldsSave" @cancel="..." />`
3. 其余逻辑（`onFieldsSave`、`editingFields`、`showFieldEditor`）保持不变

**验证**: 点击节点 → 点击"添加/编辑字段" → 对话框正确弹出并加载 fc-designer

---

### Task 3.3: 更新 shapes.ts 默认字段

**文件**: `web/src/views/apps/itsm/designer/shapes.ts`

将 `DEFAULT_NODE_FIELDS` 从 ItsmField 格式转换为 Rule 格式：

```ts
export const DEFAULT_NODE_FIELDS: Record<string, any[]> = {
  NORMAL: [
    { type: 'input', field: 'title', title: '工单标题', validate: [{ required: true }], itsmLayout: 'COL_12', itsmSortOrder: 0, props: { placeholder: '如 服务器磁盘空间不足' } },
    { type: 'input', field: 'description', title: '详细描述', validate: [{ required: true }], itsmLayout: 'COL_12', itsmSortOrder: 1, props: { type: 'textarea', rows: 3, placeholder: '请描述问题或需求详情' } },
    { type: 'select', field: 'category', title: '服务分类', validate: [{ required: true }], itsmLayout: 'COL_6', itsmSortOrder: 2, props: { options: [
      { label: '网络故障', value: 'network' }, { label: '数据库', value: 'database' },
      { label: '应用系统', value: 'application' }, { label: '安全事件', value: 'security' },
      { label: '桌面支持', value: 'desktop' }, { label: '其他', value: 'other' },
    ]}},
    { type: 'select', field: 'priority', title: '优先级', validate: [{ required: true }], itsmLayout: 'COL_6', itsmSortOrder: 3, props: { options: [
      { label: 'P1 危急', value: 'P1' }, { label: 'P2 高', value: 'P2' },
      { label: 'P3 中', value: 'P3' }, { label: 'P4 低', value: 'P4' },
    ]}},
    { type: 'ItsmFile', field: 'attachment', title: '附件', itsmLayout: 'COL_12', itsmSortOrder: 4 },
  ],
  APPROVAL: [],
  SIGN: [],
}
```

**验证**: 从 stencil 拖出 NORMAL 节点 → fields 数组为 Rule[] 格式

---

### Task 3.4: 新增 i18n 键

**文件**: `web/src/i18n/pages/itsm/zh-cn.ts`, `web/src/i18n/pages/itsm/en.ts`

新增 `designer` 命名空间下的键（如果尚不存在）：

```ts
// zh-cn.ts
designer: {
  // ... existing keys ...
  fcSave: '保存字段',
  fcCancel: '取消',
}
```

业务字段工具箱标签：
```ts
formDesigner: {
  // ... existing keys ...
  businessFields: '业务字段',
}
```

**验证**: 切换中英文 → 工具箱标签正确显示

---

## Phase 4: 渲染器替换 (1 天)

### Task 4.1: 更新 ItsmFormRenderer/index.vue

**文件**: `web/src/components/ItsmFormRenderer/index.vue`

将内部渲染逻辑改为 `<form-create>`。保留公共接口（props 签名一致）：

```vue
<template>
  <div class="ifr-wrap">
    <form-create
      v-model="formData"
      :rule="sortedRules"
      :option="formOption"
    />
    <div v-if="showSubmit" class="ifr-submit">
      <el-button @click="$emit('cancel')">{{ cancelText }}</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ submitText }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  fields?: any[]
  data?: Record<string, any>
  mode?: string
  showSubmit?: boolean
  submitText?: string
  cancelText?: string
  submitting?: boolean
}>(), { fields: () => [], data: () => ({}), mode: 'fill', showSubmit: true, submitText: '提交', submitting: false })

const emit = defineEmits<{
  'field-change': [key: string, value: any]
  submit: [data: Record<string, any>]
  cancel: []
}>()

const formData = computed({
  get: () => props.data,
  set: (v) => { /* handled via form-create v-model side effect */ },
})

const sortedRules = computed(() => {
  return [...props.fields].sort((a, b) =>
    (a.itsmSortOrder ?? 0) - (b.itsmSortOrder ?? 0)
  )
})

const formOption = computed(() => ({
  form: { size: 'default' },
  submitBtn: { show: false },
  resetBtn: { show: false },
}))

function handleSubmit() {
  emit('submit', { ...props.data })
}
</script>
```

**验证**: `npx vue-tsc --noEmit` 类型检查通过

---

### Task 4.2: 更新 TicketDetail.vue

**文件**: `web/src/views/apps/itsm/TicketDetail.vue`

改动点：
1. `ItsmFormRenderer` 的使用保持（Task 4.1 已内部改为 form-create），v-model 改为由 form-create 内部处理
2. `@field-change` 事件移除（form-create 直接用 v-model 更新 fillForm）
3. `submittedFieldLabels` 构建改为从 `rule.title` 读取：

```ts
// Before
for (const f of (st.fields || [])) {
  labels[String(f.key)] = f.name || f.key
}
// After
for (const r of (st.fields || [])) {
  labels[r.field] = r.title || r.field
}
```

4. `@submit` 事件保持不变（`onNodeSubmit(data, node)`）

**验证**: Ticket 填单页正常渲染表单，提交成功

---

### Task 4.3: 更新 ServiceDetail.vue

**文件**: `web/src/views/apps/itsm/catalog/ServiceDetail.vue`

将 `ItsmFormRenderer` 的 `@field-change` 事件改为 v-model 双向绑定（如果直接使用 form-create 而不是 ItsmFormRenderer 包装的话）。如果继续使用 Task 4.1 包装后的 `ItsmFormRenderer`，只需移除 `@field-change`。

**验证**: 服务详情页表单预览正常

---

### Task 4.4: 更新 ServiceAdmin.vue

**文件**: `web/src/views/apps/itsm/catalog/ServiceAdmin.vue`

同 ServiceDetail，适配 `form_fields` 的渲染。

**验证**: 服务管理页 `form_fields` 预览正常

---

### Task 4.5: 清理删除文件

删除以下 4 个文件：

| 文件 | 确认清单 |
|---|---|
| `web/src/views/apps/itsm/designer/FormDesigner.vue` | 确认无其他 import 引用 |
| `web/src/components/ItsmFormRenderer/ItsmFormField.vue` | 确认无其他 import 引用 |
| `web/src/components/ItsmFormRenderer/types.ts` | 确认无其他 import 引用 |
| `web/src/components/ItsmFormRenderer/fields/DateField.vue` | 确认无其他 import 引用 |

```bash
cd web/src
# Verify no remaining imports before deleting
grep -r "FormDesigner" --include="*.vue" --include="*.ts" | grep -v "FcFormDesigner\|\.spec\."
grep -r "ItsmFormField" --include="*.vue" --include="*.ts"
grep -r "from.*types" components/ItsmFormRenderer/
grep -r "DateField" --include="*.vue" --include="*.ts" | grep -v "FcDate\|\.spec\."
```

**验证**: `npx vue-tsc --noEmit` 编译通过，无 import 报错

---

## Phase 5: 后端适配 (1.5 天)

### Task 5.1: 更新 create_version()

**文件**: `backend/itsm/models/workflow.py`

找到 `Workflow.create_version()` 方法。将字段快照逻辑从读 `s.field_defs.all()` 改为读 `s.fields` JSONField：

```python
# Before (pseudocode)
workflow_fields = []
for s in states:
    workflow_fields.extend(list(s.field_defs.all()))
# Snapshot each field's attrs...

# After
workflow_fields = []
for s in states:
    for rule in (s.fields or []):
        workflow_fields.append({
            'state_node_key': s.node_key,
            'rule': rule,  # Store entire rule object as-is
        })
```

**验证**: 部署工作流 → WorkflowVersion.fields 包含 Rule[]

---

### Task 5.2: 更新 rollback()

**文件**: `backend/itsm/views/workflow_views.py`

找到 `WorkflowVersionViewSet.rollback()` 方法。将 Field 模型重建逻辑改为写回 `State.fields` JSONField：

```python
# Before: Field.objects.filter(state__workflow=workflow).delete()
#         Field.objects.create(state=state, key=..., name=..., ...)

# After: for each state in version snapshot:
#         state.fields = version.fields_for_state(state.node_key)
#         state.save(update_fields=['fields'])
```

**验证**: 版本回滚 → State.fields JSON 正确恢复

---

### Task 5.3: 更新 Preset 同步

**文件**: `backend/itsm/serializers/preset.py`

更新 `_sync_referencing_state_fields()` 和 `_sync_referencing_fields()` 以适配 `itsmPresetId` 字段：

```python
# _sync_referencing_state_fields: scan State.fields JSON for itsmPresetId
@staticmethod
def _sync_referencing_state_fields(preset):
    from itsm.models import State
    states = State.objects.filter(fields__contains=[{'itsmPresetId': preset.id}])
    for s in states:
        updated = False
        for rule in (s.fields or []):
            if rule.get('itsmPresetId') == preset.id:
                rule['props'] = rule.get('props', {})
                rule['props']['options'] = preset.value
                updated = True
        if updated:
            s.save(update_fields=['fields'])

# _sync_referencing_fields: adapt to also scan State.fields JSON
@staticmethod
def _sync_referencing_fields(preset):
    # Old: Field.objects.filter(preset=preset).update(choice=preset.value)
    # Keep for backward compat, but primary sync is now via _sync_referencing_state_fields
    from itsm.models.field import Field
    Field.objects.filter(preset=preset).update(choice=preset.value)
```

**验证**: 修改 Preset → 关联字段的选项自动更新

---

### Task 5.4: 标记 FieldSerializer deprecated

**文件**: `backend/itsm/serializers/workflow_serializers.py`

```python
class FieldSerializer(CustomModelSerializer):
    """
    DEPRECATED since 2026-07-12.
    Field model is superseded by State.fields JSONField.
    Retained for read-only access; write operations should use State.fields directly.
    """
    class Meta:
        model = Field
        fields = '__all__'
```

### Task 5.5: 改造 batch_update

**文件**: `backend/itsm/views/workflow_views.py`

将 `FieldViewSet.batch_update()` 从写 Field 模型改为写 `State.fields` JSONField：

```python
@action(detail=False, methods=['post'])
def batch_update(self, request):
    state_id = request.data.get('state_id')
    fields_data = request.data.get('fields', [])
    state = State.objects.get(id=state_id)
    state.fields = fields_data  # Direct assignment of Rule[]
    state.save(update_fields=['fields'])
    return DetailResponse(data={'fields': state.fields})
```

**验证**: `POST /api/itsm/fields/batch_update/` → State.fields JSON 正确写入

---

## Phase 6: 全流程验证 (2 天)

### Task 6.1: 前端构建检查

```bash
cd web
npx vue-tsc --noEmit     # TypeScript 类型检查
npm run build             # 构建无报错
```

### Task 6.2: 设计态验证

1. 打开工作流设计器 → 拖入 NORMAL 节点
2. 点击"添加/编辑字段" → FcFormDesigner 正常渲染
3. 拖入基础字段 (input, select, radio, datePicker) → 画布无报错
4. 拖入业务字段 (ItsmMembers, ItsmFile, ItsmCascader, ItsmSection) → 自定义组件显示
5. 选中字段 → 右侧属性面板可编辑
6. 预览模式 → 表单渲染正确
7. 保存工作流 → `State.fields` 存储 Rule[]
8. 重新打开 → 字段正确回显 (setRule)

### Task 6.3: 运行态验证

1. 创建 Ticket → 进入 NORMAL 填单节点
2. 所有字段类型可正常交互
3. MEMBERS 可搜索用户并多选
4. FILE 可上传附件
5. CASCADE 可展开级联选择
6. 必填字段为空时阻止提交
7. 提交 → formData 正确发送到 `node_submit`

### Task 6.4: 回归验证

1. 现有工作流模板加载正常（NodeConfigPanel, EdgeConfigPanel）
2. Trigger 配置保存/加载正常
3. SLA 策略不受影响
4. Preset CRUD 功能正常
5. OpsFlow PropertyPanel 正常（RenderForm/tags 未删除）
6. ServiceDetail / ServiceAdmin 表单预览正常

### Task 6.5: 后端测试

```bash
cd backend
python manage.py test itsm.tests
python manage.py test itsm.tests.test_workflow
```

---

## 依赖关系图

```
Phase 1 (env setup)
  └─> Phase 2 (custom components)
        └─> Phase 3 (designer integration)
              └─> Phase 4 (renderer replacement)
        └─> Phase 5 (backend) [可并行]
  └─> Phase 6 (verification) [依赖 Phase 3+4+5]

Phase 2 内部顺序:
  Task 2.1 (fcExtensions.ts 骨架)
    ├─> Task 2.2 (FcSectionDivider — 最简单先通流程)
    ├─> Task 2.3-2.7 (其余 4 个自定义组件 — 可并行)
    └─> Task 2.8 (DATE 确认内置替代)
```

---

## 工时汇总

| Phase | 内容 | 估时 |
|---|---|---|
| 1 | 环境搭建 | 0.5 天 |
| 2 | 自定义组件与扩展 | 3.5 天 |
| 3 | 设计器集成 | 1.5 天 |
| 4 | 渲染器替换 | 1 天 |
| 5 | 后端适配 | 1.5 天 |
| 6 | 全流程验证 | 2 天 |
| **合计** | | **10 天** |
