import { ref, reactive } from 'vue'
import type { Config, DragRule, Menu } from '@form-create/designer'
import FcDesigner from '@form-create/designer'
import formCreate from '@form-create/element-ui'
import FcMembersField from '/@/components/ItsmFormRenderer/fields/FcMembersField.vue'
import FcFileField from '/@/components/ItsmFormRenderer/fields/FcFileField.vue'
import FcRichtextField from '/@/components/ItsmFormRenderer/fields/FcRichtextField.vue'
import FcTableField from '/@/components/ItsmFormRenderer/fields/FcTableField.vue'
import FcCascaderField from '/@/components/ItsmFormRenderer/fields/FcCascaderField.vue'
import FcSectionDivider from '/@/components/ItsmFormRenderer/fields/FcSectionDivider.vue'

// ── Reactive preset options & full data (populated by FcFormDesigner after load) ──
export const presetOptionList = ref<{ label: string; value: number }[]>([])
export const presetDataMap = new Map<number | string, any[]>()

// ── Designer Settings Persistence ──

function getProjectId(): string {
  return localStorage.getItem('opsflow_active_project_id') || '0'
}

function storageKey() { return `fc_designer_settings_${getProjectId()}` }
function apiUrl() {
  return `/api/itsm/fc-designer-settings/?project_id=${getProjectId()}`
}

/** Config keys that users can toggle via the settings panel */
export const SHOW_KEYS = [
  // Left sidebar icons
  'showLanguage', 'showJsonPreview', 'showDevice',
  // Top toolbar
  'showPreviewBtn', 'showInputData',
  // Right panel master
  'showConfig',
  // Function toggles
  'hotKey', 'autoResetField', 'autoResetName',
  'fieldReadonly', 'nameReadonly',
  'hiddenDragMenu', 'hiddenDragBtn', 'exitConfirm',
  // Right panel sections
  'showFormConfig', 'showBaseForm', 'showPropsForm', 'showStyleForm',
  'showEventForm', 'showValidateForm', 'validateOnlyRequired',
  'showComponentName', 'showControl', 'showCustomProps', 'showAdvancedForm',
  // Toolbar extras
  'showTemplate', 'showQuickLayout', 'showGridLine', 'showAi',
] as const

/** Menu groups with their built-in components for fine-grained toggling */
export interface MenuGroupDef {
  name: string
  label: string
  items: { name: string; label: string }[]
}
export const MENU_GROUPS: MenuGroupDef[] = [
  {
    name: 'main', label: '基础组件', items: [
      { name: 'input', label: '单行文本' }, { name: 'textarea', label: '多行文本' },
      { name: 'password', label: '密码' }, { name: 'number', label: '数字' },
      { name: 'radio', label: '单选' }, { name: 'checkbox', label: '多选' },
      { name: 'select', label: '下拉选择' }, { name: 'switch', label: '开关' },
      { name: 'rate', label: '评分' }, { name: 'slider', label: '滑块' },
      { name: 'date', label: '日期' }, { name: 'time', label: '时间' },
      { name: 'color', label: '颜色' }, { name: 'cascader', label: '级联' },
      { name: 'upload', label: '上传' }, { name: 'tree', label: '树形' },
      { name: 'treeSelect', label: '树选择' }, { name: 'editor', label: '富文本' },
      { name: 'tag', label: '标签' }, { name: 'title', label: '标题' },
      { name: 'image', label: '图片' },
    ],
  },
  {
    name: 'subform', label: '子表单组件', items: [
      { name: 'group', label: '分组' }, { name: 'subForm', label: '子表单' },
    ],
  },
  {
    name: 'aide', label: '辅助组件', items: [
      { name: 'alert', label: '提示' }, { name: 'button', label: '按钮' },
      { name: 'text', label: '文本' }, { name: 'html', label: 'HTML' },
      { name: 'divider', label: '分割线' }, { name: 'space', label: '间距' },
    ],
  },
  {
    name: 'layout', label: '布局组件', items: [
      { name: 'row', label: '行' }, { name: 'col', label: '列' },
      { name: 'tabs', label: '标签页' }, { name: 'tabPane', label: '标签面板' },
      { name: 'card', label: '卡片' }, { name: 'collapse', label: '折叠面板' },
      { name: 'table', label: '表格布局' },
    ],
  },
]

const DEFAULT_CONFIG: Config = {
  showSaveBtn: false,
  showPrintBtn: false,
  showImportBtn: false,
  showTemplate: false,
  showDevice: false,
  showLanguage: false,
  showJsonPreview: false,
  showGridLine: false,
  showQuickLayout: false,
  showInputData: false,
  showPreviewBtn: true,
  showConfig: true,
  showBaseForm: true,
  showPropsForm: true,
  showStyleForm: false,
  showEventForm: false,
  showValidateForm: true,
  showFormConfig: false,
  showAdvancedForm: false,
  showComponentName: false,
  showControl: false,
  showCustomProps: false,
  showAi: false,
  // Behavior
  autoActive: true,
  checkFieldUnique: true,
  autoResetField: false,
  autoResetName: false,
  fieldReadonly: false,
  nameReadonly: false,
  hiddenDragMenu: false,
  hiddenDragBtn: false,
  hotKey: true,
  exitConfirm: false,
  validateOnlyRequired: false,
}

// ── Designer instance ref (set by FcFormDesigner.vue on mount) ──
let _d: any = null
export function setDesignerInstance(d: any) { _d = d }
export function getDesignerInstance() { return _d }

// ── Designer Config (reactive — toggles in settings panel take effect immediately) ──

export const designerConfig = reactive<Config>({ ...DEFAULT_CONFIG })

/** Load settings: localStorage → DB API → defaults. Call once on design-time mount. */
export async function initDesignerSettings() {
  // 1. Try localStorage first (instant)
  try {
    const saved = localStorage.getItem(storageKey())
    if (saved) {
      const parsed = JSON.parse(saved)
      for (const key of SHOW_KEYS) {
        if (key in parsed) (designerConfig as any)[key] = parsed[key]
      }
      if (parsed._hiddenMenu) (designerConfig as any).hiddenMenu = parsed._hiddenMenu
      if (parsed._hiddenItem) (designerConfig as any).hiddenItem = parsed._hiddenItem
      return
    }
  } catch { /* fall through */ }

  // 2. localStorage miss → try DB
  try {
    const res = await fetch(apiUrl())
    const json = await res.json()
    if (json.data && Object.keys(json.data).length) {
      for (const key of SHOW_KEYS) {
        if (key in json.data) (designerConfig as any)[key] = json.data[key]
      }
      if (json.data._hiddenMenu) (designerConfig as any).hiddenMenu = json.data._hiddenMenu
      if (json.data._hiddenItem) (designerConfig as any).hiddenItem = json.data._hiddenItem
      // Backfill localStorage
      localStorage.setItem(storageKey(), JSON.stringify(json.data))
      return
    }
  } catch { /* fall through */ }

  // 3. Neither available → defaults already set
}

/** Save current toggle values to localStorage (sync) + DB (async fire-and-forget). */
export function saveDesignerSettings() {
  const toSave: Record<string, any> = {}
  for (const key of SHOW_KEYS) {
    toSave[key] = (designerConfig as any)[key]
  }
  toSave._hiddenMenu = (designerConfig as any).hiddenMenu || []
  toSave._hiddenItem = (designerConfig as any).hiddenItem || []
  localStorage.setItem(storageKey(), JSON.stringify(toSave))
  // Async DB write (fire-and-forget — don't block UI)
  fetch(apiUrl(), {
    method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toSave),
    }).catch(() => { /* silent */ })
}

/** Reset to code defaults + clear localStorage + clear DB. */
export function resetDesignerSettings() {
  for (const key of SHOW_KEYS) {
    (designerConfig as any)[key] = (DEFAULT_CONFIG as any)[key]
  }
  (designerConfig as any).hiddenMenu = []
  ;(designerConfig as any).hiddenItem = []
  localStorage.removeItem(storageKey())
  fetch(apiUrl(), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  }).catch(() => { /* silent */ })
}

// ── Custom Toolbox Menu ──

export const customMenu: Menu[] = [
  {
    name: 'main', title: '基础字段', list: [
      { name: 'input', label: '单行文本', icon: 'icon-input' },
      { name: 'textarea', label: '多行文本', icon: 'icon-textarea' },
      { name: 'number', label: '整数', icon: 'icon-number' },
      { name: 'datePicker', label: '日期', icon: 'icon-date' },
      { name: 'select', label: '下拉选择', icon: 'icon-select' },
      { name: 'radio', label: '单选', icon: 'icon-radio' },
      { name: 'checkbox', label: '复选框', icon: 'icon-checkbox' },
    ],
  },
  {
    name: 'itsm', title: '业务字段', list: [
      { name: 'ItsmMembers', label: '人员选择', icon: 'icon-user' },
      { name: 'ItsmFile', label: '附件', icon: 'icon-upload' },
      { name: 'ItsmRichtext', label: '富文本', icon: 'icon-editor' },
      { name: 'ItsmTable', label: '子表格', icon: 'icon-table' },
      { name: 'ItsmCascader', label: '级联', icon: 'icon-cascader' },
      { name: 'ItsmSection', label: '分组', icon: 'icon-divider' },
    ],
  },
]

// ── DragRule Definitions ──

export const membersDR: DragRule = {
  name: 'ItsmMembers',
  label: '人员选择',
  icon: 'icon-user',
  menu: 'itsm',
  input: true,
  rule() {
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

export const fileDR: DragRule = {
  name: 'ItsmFile',
  label: '附件',
  icon: 'icon-upload',
  menu: 'itsm',
  input: true,
  rule() {
    return {
      type: 'ItsmFile',
      field: `file_${Date.now()}`,
      title: '附件',
      itsmLayout: 'COL_12',
      itsmSortOrder: 0,
      props: { limit: 1, btnText: '点击上传' },
    }
  },
  props() {
    return [
      { type: 'input', field: 'btnText', title: '按钮文字' },
      { type: 'number', field: 'limit', title: '最大数量', value: 1 },
      { type: 'input', field: 'accept', title: '文件类型' },
      { type: 'input', field: 'action', title: '上传地址' },
      { type: 'switch', field: 'disabled', title: '禁用' },
    ]
  },
  validate: ['required'],
}

export const richtextDR: DragRule = {
  name: 'ItsmRichtext',
  label: '富文本',
  icon: 'icon-editor',
  menu: 'itsm',
  input: true,
  rule() {
    return {
      type: 'ItsmRichtext',
      field: `richtext_${Date.now()}`,
      title: '富文本',
      itsmLayout: 'COL_12',
      itsmSortOrder: 0,
      props: { rows: 6, placeholder: '请输入内容' },
    }
  },
  props() {
    return [
      { type: 'number', field: 'rows', title: '行数', value: 6 },
      { type: 'input', field: 'placeholder', title: '占位文字' },
      { type: 'switch', field: 'disabled', title: '禁用' },
    ]
  },
}

export const tableDR: DragRule = {
  name: 'ItsmTable',
  label: '子表格',
  icon: 'icon-table',
  menu: 'itsm',
  input: true,
  rule() {
    return {
      type: 'ItsmTable',
      field: `table_${Date.now()}`,
      title: '子表格',
      itsmLayout: 'COL_12',
      itsmSortOrder: 0,
      props: {
        columns: [
          { field: 'name', title: '名称', type: 'input' },
          { field: 'value', title: '值', type: 'input' },
        ],
      },
    }
  },
  props() {
    return [{ type: 'switch', field: 'disabled', title: '禁用' }]
  },
}

export const cascaderDR: DragRule = {
  name: 'ItsmCascader',
  label: '级联',
  icon: 'icon-cascader',
  menu: 'itsm',
  input: true,
  rule() {
    return {
      type: 'ItsmCascader',
      field: `cascade_${Date.now()}`,
      title: '级联',
      itsmLayout: 'COL_12',
      itsmSortOrder: 0,
      props: { placeholder: '请选择' },
    }
  },
  props() {
    return [
      { type: 'input', field: 'placeholder', title: '占位文字' },
      { type: 'switch', field: 'disabled', title: '禁用' },
      { type: 'switch', field: 'multiple', title: '多选' },
    ]
  },
  validate: ['required'],
}

export const sectionDR: DragRule = {
  name: 'ItsmSection',
  label: '分组',
  icon: 'icon-divider',
  menu: 'itsm',
  input: false,
  mask: false,
  rule() {
    return {
      type: 'ItsmSection',
      title: '新分组',
      itsmLayout: 'COL_12',
      itsmSortOrder: 0,
      props: { label: '新分组' },
    }
  },
  props() {
    return [
      { type: 'input', field: 'label', title: '分组名称' },
    ]
  },
}

// Shared watch: loads preset data, refreshes canvas + re-activates panel
function onPresetWatch({ rule, value }: any) {
  if (value == null || value === '') return
  const opts = presetDataMap.get(Number(value)) || presetDataMap.get(String(value))
  if (!opts) return
  const data = JSON.parse(JSON.stringify(opts))
  const d = getDesignerInstance()
  if (!d) return
  const rules = d.getRule()
  let activeRule: any = null
  for (const r of rules) {
    if (r.field === rule.field) {
      r.options = data
      if (!r.props) r.props = {}
      r.props.options = data
      r._optionType = 2
      activeRule = r
    }
  }
  if (activeRule) {
    d.setRule(rules)
    d.triggerActive(activeRule)
  }
}

// Extended _optionType with "从预设加载" in table editor & sample data in text/json modes
function makeOptionsRule(t: any, to: string) {
  return {
    type: 'select', field: '_optionType', value: 2,
    options: [
      { label: '表格配置', value: 2 }, { label: '文本输入', value: 4 },
      { label: 'JSON输入', value: 5 }, { label: '远程请求', value: 1 },
    ],
    control: [
      { value: 1, rule: [{ type: 'FetchConfig', field: 'formCreateEffect>fetch', title: '远程请求' }] },
      { value: 2, rule: [
        { type: 'select', field: 'itsmPresetId', title: '从预设加载',
          props: { clearable: true, placeholder: '选择预设自动填充选项' },
          options: presetOptionList.value },
        { type: 'TableOptions', field: `formCreateProps>${to}`, title: '选项' },
      ]},
      { value: 4, rule: [{ type: 'OptionTextInput', field: `formCreateProps>${to}`, title: '选项',
        info: 'One option per line: value=label or just label',
        props: { placeholder: 'val1=Option 1\nval2=Option 2\nOption 3' } }] },
      { value: 5, rule: [{ type: 'Struct', field: `formCreateProps>${to}`, title: '选项',
        info: 'JSON array:',
        props: { placeholder: '[{"label":"Option 1","value":"val1"},{"label":"Option 2","value":"val2"}]' } }] },
    ],
  }
}

export const selectPresetDR: DragRule = {
  name: 'select', label: '下拉选择', icon: 'icon-select', menu: 'main', input: true,
  rule() {
    return { type: 'select', field: `sel_${Date.now()}`, title: '下拉选择', props: {}, options: [] }
  },
  props(_: any, { t }: any) {
    return [
      { type: 'hidden', field: 'itsmPresetId' },
      makeOptionsRule(t, 'options'),
      { type: 'switch', field: 'multiple', title: '多选' },
      { type: 'switch', field: 'disabled', title: '禁用' },
      { type: 'switch', field: 'clearable', title: '可清空' },
      { type: 'input', field: 'placeholder', title: '占位文字' },
      { type: 'switch', field: 'filterable', title: '可搜索' },
    ]
  },
  watch: { itsmPresetId: onPresetWatch },
} as any

export const radioPresetDR: DragRule = {
  name: 'radio', label: '单选', icon: 'icon-radio', menu: 'main', input: true,
  rule() {
    return { type: 'radio', field: `radio_${Date.now()}`, title: '单选', props: {}, options: [] }
  },
  props(_: any, { t }: any) {
    return [
      { type: 'hidden', field: 'itsmPresetId' },
      makeOptionsRule(t, 'options'),
      { type: 'switch', field: 'disabled', title: '禁用' },
      { type: 'switch', field: 'type', title: '按钮样式', props: { activeValue: 'button', inactiveValue: 'default' } },
    ]
  },
  watch: { itsmPresetId: onPresetWatch },
} as any

export const checkboxPresetDR: DragRule = {
  name: 'checkbox', label: '多选', icon: 'icon-checkbox', menu: 'main', input: true,
  rule() {
    return { type: 'checkbox', field: `cb_${Date.now()}`, title: '多选', props: {}, options: [] }
  },
  props(_: any, { t }: any) {
    return [
      { type: 'hidden', field: 'itsmPresetId' },
      makeOptionsRule(t, 'options'),
      { type: 'switch', field: 'disabled', title: '禁用' },
      { type: 'switch', field: 'type', title: '按钮样式', props: { activeValue: 'button', inactiveValue: 'default' } },
    ]
  },
  watch: { itsmPresetId: onPresetWatch },
} as any

// ── Registration Entry ──

export function registerRuntimeComponents() {
  // Register runtime rendering components (form-create side). Must run at app
  // startup so ANY page using <form-create> (service catalog, ticket detail,
  // submit wizard) can resolve Itsm* field types — not just the designer.
  formCreate.component('ItsmMembers', FcMembersField)
  formCreate.component('ItsmFile', FcFileField)
  formCreate.component('ItsmRichtext', FcRichtextField)
  formCreate.component('ItsmTable', FcTableField)
  formCreate.component('ItsmCascader', FcCascaderField)
  formCreate.component('ItsmSection', FcSectionDivider)
}

export function registerCustomComponents(designer: any) {
  // Register runtime rendering components (form-create side)
  registerRuntimeComponents()

  // Register design-time rendering components (FcDesigner side)
  FcDesigner.component('ItsmMembers', FcMembersField)
  FcDesigner.component('ItsmFile', FcFileField)
  FcDesigner.component('ItsmRichtext', FcRichtextField)
  FcDesigner.component('ItsmTable', FcTableField)
  FcDesigner.component('ItsmCascader', FcCascaderField)
  FcDesigner.component('ItsmSection', FcSectionDivider)

  // Add custom toolbox menu group
  designer.addMenu({ name: 'itsm', title: '业务字段' })

  // Register ITSM custom DragRules
  designer.addComponent([selectPresetDR, radioPresetDR, checkboxPresetDR])
  designer.addComponent([
    membersDR, fileDR, richtextDR, tableDR, cascaderDR, sectionDR,
  ])
}
