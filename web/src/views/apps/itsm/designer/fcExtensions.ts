import { ref } from 'vue'
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

// ── Designer Config ──

export const designerConfig: Config = {
  // All built-in menu groups and components are available by default.
  // Use hiddenMenu / hiddenItem to selectively hide; use componentPermission to disable.
  // hiddenMenu: ['subform', 'chart', 'aide', 'template'],
  // hiddenItem: ['switch', 'rate', 'slider', ...],
  // Feature toggles — ITSM manages save via its own dialog footer
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
  showConfig: true,
  showBaseForm: true,
  showPropsForm: true,
  showValidateForm: true,
  // Behavior
  autoActive: true,
  checkFieldUnique: true,
  autoResetField: false,   // ITSM uses semantic field keys
  autoResetName: false,

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

// ── Registration Entry ──

export function registerCustomComponents(designer: any) {
  // Register runtime rendering components (form-create side)
  formCreate.component('ItsmMembers', FcMembersField)
  formCreate.component('ItsmFile', FcFileField)
  formCreate.component('ItsmRichtext', FcRichtextField)
  formCreate.component('ItsmTable', FcTableField)
  formCreate.component('ItsmCascader', FcCascaderField)
  formCreate.component('ItsmSection', FcSectionDivider)

  // Register design-time rendering components (FcDesigner side)
  FcDesigner.component('ItsmMembers', FcMembersField)
  FcDesigner.component('ItsmFile', FcFileField)
  FcDesigner.component('ItsmRichtext', FcRichtextField)
  FcDesigner.component('ItsmTable', FcTableField)
  FcDesigner.component('ItsmCascader', FcCascaderField)
  FcDesigner.component('ItsmSection', FcSectionDivider)

  // Add custom toolbox menu group
  designer.addMenu({ name: 'itsm', title: '业务字段' })

  // Register DragRules
  designer.addComponent([
    membersDR, fileDR, richtextDR, tableDR, cascaderDR, sectionDR,
  ])
}
