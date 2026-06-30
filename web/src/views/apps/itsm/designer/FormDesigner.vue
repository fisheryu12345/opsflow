<template>
  <div class="fd-wrap">
    <!-- Left: Toolbox -->
    <div class="fd-toolbox" v-if="!previewMode">
      <div class="fd-toolbox-title">字段类型</div>
      <div v-for="grp in fieldTypeGroups" :key="grp.group" class="fd-tg">
        <div class="fd-tg-label">{{ grp.group }}</div>
        <VueDraggable :list="grp.types" :group="{ name: 'form-fields', pull: 'clone', put: false }"
          :sort="false" :clone="(t: any) => createDefaultField(t.type)" item-key="type" class="fd-tg-list">
          <template #item="{ element }">
            <div class="fd-tg-item">{{ element.label }}</div>
          </template>
        </VueDraggable>
      </div>
    </div>

    <!-- Center: Canvas -->
    <div class="fd-canvas">
      <div class="fd-canvas-title">
        <span>{{ previewMode ? '🔍 预览模式' : '表单设计' }}</span>
        <div class="fd-canvas-actions">
          <!-- Global column selector (design mode only) -->
          <template v-if="!previewMode">
            <span class="fd-col-label">列数:</span>
            <div class="fd-col-btns">
              <button v-for="col in columnPresets" :key="col.cols"
                class="fd-col-btn" :class="{ active: activeColumnPreset === col.cols }"
                @click="setGlobalColumns(col.cols)" :title="col.label">
                <span v-for="i in col.cols" :key="i" class="fd-col-dot" />
              </button>
            </div>
            <span class="fd-col-divider" />
          </template>
          <el-button size="small" :type="previewMode ? 'primary' : 'default'" @click="previewMode = !previewMode">
            {{ previewMode ? '退出预览' : '预览工单' }}
          </el-button>
        </div>
      </div>
      <div class="fd-canvas-body">
        <div v-if="!localFields.length" class="fd-canvas-empty">
          从左侧拖入字段类型到此处
        </div>
        <div v-if="previewMode" class="fd-drag-list">
          <div v-for="(element, index) in localFields" :key="element.key"
            class="fd-field-wrap" :class="[layoutClass(element.layout), { 'fd-sec-wrap': element.type === 'SECTION' }]">
            <!-- Section type -->
            <div v-if="element.type === 'SECTION'" class="fd-sec">
              <div class="fd-sec-title">
                <el-icon><FolderOpened /></el-icon>
                {{ element.name || '未命名分组' }}
              </div>
              <div class="fd-sec-line" />
            </div>
            <template v-else>
              <div class="fd-field-label">
                {{ element.name || element.key }}
                <span v-if="element.required" class="fd-req">*</span>
              </div>
              <el-input v-if="element.type === 'STRING'" size="small" :placeholder="element.placeholder || '请输入'" />
              <el-input v-else-if="element.type === 'TEXT'" type="textarea" :rows="2" size="small" :placeholder="element.placeholder || '请输入'" />
              <el-input-number v-else-if="element.type === 'INT'" size="small" :min="0" style="width:100%" />
              <el-date-picker v-else-if="element.type === 'DATE'" type="date" size="small" style="width:100%" />
              <el-date-picker v-else-if="element.type === 'DATETIME'" type="datetime" size="small" style="width:100%" />
              <el-select v-else-if="element.type === 'SELECT'" size="small" style="width:100%" :placeholder="'请选择'">
                <el-option v-for="c in element.choice || []" :key="c.value" :label="c.label" :value="c.value" />
              </el-select>
              <el-radio-group v-else-if="element.type === 'RADIO'">
                <el-radio v-for="c in element.choice || []" :key="c.value" :value="c.value" style="margin-right:12px">{{ c.label }}</el-radio>
              </el-radio-group>
              <el-checkbox-group v-else-if="element.type === 'CHECKBOX'">
                <el-checkbox v-for="c in element.choice || []" :key="c.value" :value="c.value" style="margin-right:12px">{{ c.label }}</el-checkbox>
              </el-checkbox-group>
              <el-select v-else-if="element.type === 'MULTISELECT'" size="small" multiple style="width:100%" :placeholder="'多选'">
                <el-option v-for="c in element.choice || []" :key="c.value" :label="c.label" :value="c.value" />
              </el-select>
              <el-select v-else-if="element.type === 'MEMBERS'" size="small" filterable style="width:100%" :placeholder="'选择人员'" />
              <div v-else-if="element.type === 'FILE'" class="fd-placeholder">📎 文件上传区域</div>
              <div v-else-if="element.type === 'RICHTEXT'" class="fd-placeholder fd-rich">📝 富文本编辑器</div>
              <div v-else-if="element.type === 'TABLE'" class="fd-placeholder">⊞ 子表格</div>
              <el-cascader v-else-if="element.type === 'CASCADE'" size="small" style="width:100%" :placeholder="'请选择'" />
              <el-input v-else size="small" :placeholder="element.type" />
            </template>
          </div>
        </div>
        <VueDraggable v-else v-model="localFields" group="form-fields" item-key="key" class="fd-drag-list"
          @change="onSortChange">
          <template #item="{ element, index }">
            <div class="fd-field-wrap" :class="[layoutClass(element.layout), { 'fd-selected': selectedIndex === index, 'fd-sec-wrap': element.type === 'SECTION' }]" @click.stop="selectField(index)">
              <!-- Section type -->
              <div v-if="element.type === 'SECTION'" class="fd-sec">
                <div class="fd-sec-title">
                  <el-icon><FolderOpened /></el-icon>
                  {{ element.name || '未命名分组' }}
                </div>
                <div class="fd-sec-line" />
              </div>
              <!-- Regular field preview -->
              <template v-else>
                <div class="fd-field-label">
                  {{ element.name || element.key }}
                  <span v-if="element.required" class="fd-req">*</span>
                  <span class="fd-field-type-tag">{{ typeLabel(element.type) }}</span>
                </div>
                <!-- STRING -->
                <el-input v-if="element.type === 'STRING'" size="small" :placeholder="element.placeholder || '请输入'" disabled />
                <el-input v-else-if="element.type === 'TEXT'" type="textarea" :rows="2" size="small" :placeholder="element.placeholder || '请输入'" disabled />
                <el-input-number v-else-if="element.type === 'INT'" size="small" :min="0" disabled style="width:100%" />
                <el-date-picker v-else-if="element.type === 'DATE'" type="date" size="small" disabled style="width:100%" />
                <el-date-picker v-else-if="element.type === 'DATETIME'" type="datetime" size="small" disabled style="width:100%" />
                <el-select v-else-if="element.type === 'SELECT'" size="small" disabled style="width:100%" :placeholder="'请选择'">
                  <el-option v-for="c in element.choice || []" :key="c.value" :label="c.label" :value="c.value" />
                </el-select>
                <el-radio-group v-else-if="element.type === 'RADIO'" disabled>
                  <el-radio v-for="c in element.choice || []" :key="c.value" :value="c.value" style="margin-right:12px">{{ c.label }}</el-radio>
                </el-radio-group>
                <el-checkbox-group v-else-if="element.type === 'CHECKBOX'" disabled>
                  <el-checkbox v-for="c in element.choice || []" :key="c.value" :value="c.value" style="margin-right:12px">{{ c.label }}</el-checkbox>
                </el-checkbox-group>
                <el-select v-else-if="element.type === 'MULTISELECT'" size="small" multiple disabled style="width:100%" :placeholder="'多选'">
                  <el-option v-for="c in element.choice || []" :key="c.value" :label="c.label" :value="c.value" />
                </el-select>
                <el-select v-else-if="element.type === 'MEMBERS'" size="small" filterable disabled style="width:100%" :placeholder="'选择人员'" />
                <div v-else-if="element.type === 'FILE'" class="fd-placeholder">📎 文件上传区域</div>
                <div v-else-if="element.type === 'RICHTEXT'" class="fd-placeholder fd-rich">📝 富文本编辑器</div>
                <div v-else-if="element.type === 'TABLE'" class="fd-placeholder">⊞ 子表格</div>
                <el-cascader v-else-if="element.type === 'CASCADE'" size="small" disabled style="width:100%" :placeholder="'请选择'" />
                <el-input v-else size="small" disabled :placeholder="element.type" />
                <!-- Field actions -->
                <div class="fd-actions" @click.stop>
                  <el-button size="small" text @click="onCopyField(index)"><el-icon><CopyDocument /></el-icon></el-button>
                  <el-button size="small" text type="danger" @click="localFields.splice(index, 1)"><el-icon><Delete /></el-icon></el-button>
                </div>
              </template>
            </div>
          </template>
        </VueDraggable>
        <div class="fd-add-sec" @click="addSection">+ 添加分组</div>
      </div>
    </div>

    <!-- Right: Property panel -->
    <div class="fd-props" v-if="selectedField && !previewMode">
      <div class="fd-props-title">字段属性</div>
      <el-form size="small" label-position="top">
        <template v-if="selectedField.type !== 'SECTION'">
          <el-form-item label="标识 (key)">
            <el-input v-model="selectedField.key" />
          </el-form-item>
          <el-form-item label="名称">
            <el-input v-model="selectedField.name" />
          </el-form-item>
          <el-form-item label="提示文字">
            <el-input v-model="selectedField.placeholder" placeholder="选填" />
          </el-form-item>
          <el-form-item label="必填">
            <el-switch v-model="selectedField.required" />
          </el-form-item>
          <el-form-item label="列宽">
            <el-radio-group v-model="selectedField.layout">
              <el-radio value="COL_12">整行</el-radio>
              <el-radio value="COL_8">2/3</el-radio>
              <el-radio value="COL_6">1/2</el-radio>
              <el-radio value="COL_4">1/3</el-radio>
              <el-radio value="COL_3">1/4</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="默认值">
            <el-input v-if="['STRING','TEXT'].includes(selectedField.type)" v-model="selectedField.default" />
            <el-select v-else-if="selectedField.type === 'SELECT'" v-model="selectedField.default" clearable size="small" style="width:100%">
              <el-option v-for="c in selectedField.choice || []" :key="c.value" :label="c.label" :value="c.value" />
            </el-select>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="分组标题">
            <el-input v-model="selectedField.name" placeholder="如 基本信息" />
          </el-form-item>
        </template>

        <!-- Choices editor (SELECT/RADIO/CHECKBOX/MULTISELECT) -->
        <div v-if="showChoicesEditor(selectedField.type)" class="fd-choices">
          <div class="fd-choices-title">选项列表
            <el-button size="small" text @click="addChoice">+ 添加</el-button>
          </div>
          <div v-for="(c, ci) in selectedField.choice" :key="ci" class="fd-choice-row">
            <el-input v-model="c.label" size="small" placeholder="显示名" style="flex:1" />
            <el-input v-model="c.value" size="small" placeholder="值" style="flex:1;margin:0 4px" />
            <el-button size="small" text type="danger" @click="selectedField.choice.splice(ci, 1)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <div v-if="!selectedField.choice?.length" class="fd-choices-empty">暂无选项</div>
        </div>

        <!-- Show condition -->
        <el-form-item label="显示条件">
          <el-switch v-model="showConditionEnabled" />
        </el-form-item>
        <template v-if="showConditionEnabled">
          <el-form-item label="条件字段">
            <el-select v-model="selectedField.show_conditions.field" filterable style="width:100%">
              <el-option v-for="f in availableConditionFields" :key="f.key" :label="f.name || f.key" :value="f.key" />
            </el-select>
          </el-form-item>
          <el-form-item label="条件值">
            <el-input v-model="selectedField.show_conditions.value" placeholder="等于" />
          </el-form-item>
        </template>
      </el-form>
    </div>
    <div v-else-if="!previewMode" class="fd-props fd-props-empty">
      <span style="color:#C0C4CC">点击字段编辑属性</span>
    </div>
  </div>
  <div class="fd-footer">
    <el-button @click="emit('cancel')">取消</el-button>
    <el-button type="primary" @click="emit('save', localFields)">保存设计</el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Delete, CopyDocument, FolderOpened } from '@element-plus/icons-vue'
import VueDraggable from 'vuedraggable'

const props = defineProps<{ fields?: any[] }>()
const emit = defineEmits<{ save: [fields: any[]]; cancel: [] }>()

interface Field { key: string; name?: string; type: string; required: boolean; layout: string; choice?: any[]; default?: any; placeholder?: string; sort_order?: number; show_conditions?: any }

const localFields = ref<Field[]>([])
const selectedIndex = ref<number | null>(null)
const showConditionEnabled = ref(false)
const previewMode = ref(false)

const columnPresets = [
  { cols: 4, label: '4列', layout: 'COL_3' },
  { cols: 3, label: '3列', layout: 'COL_4' },
  { cols: 2, label: '2列', layout: 'COL_6' },
  { cols: 1, label: '1列', layout: 'COL_12' },
]
const activeColumnPreset = ref(1)

function setGlobalColumns(cols: number) {
  activeColumnPreset.value = cols
  const preset = columnPresets.find(p => p.cols === cols)
  if (preset) {
    localFields.value.forEach(f => { if (f.type !== 'SECTION') f.layout = preset.layout })
  }
}

// Initialize from props
watch(() => props.fields, (f) => {
  localFields.value = f ? JSON.parse(JSON.stringify(f)) : []
  selectedIndex.value = null
}, { immediate: true })

const selectedField = computed(() => {
  if (selectedIndex.value === null) return null
  return localFields.value[selectedIndex.value] || null
})

// Available condition fields (fields before current)
const availableConditionFields = computed(() => {
  if (selectedIndex.value === null) return []
  return localFields.value.slice(0, selectedIndex.value).filter(f => f.type !== 'SECTION')
})

// Field type groups for toolbox
interface FieldTypeDef { type: string; label: string }
interface FieldTypeGroup { group: string; types: FieldTypeDef[] }
const fieldTypeGroups = ref<FieldTypeGroup[]>([
  { group: '基础字段', types: [
    { type: 'STRING', label: '单行文本' }, { type: 'TEXT', label: '多行文本' },
    { type: 'INT', label: '整数' }, { type: 'DATE', label: '日期' },
    { type: 'DATETIME', label: '日期时间' },
  ]},
  { group: '选择类', types: [
    { type: 'SELECT', label: '下拉选择' }, { type: 'RADIO', label: '单选' },
    { type: 'CHECKBOX', label: '复选框' }, { type: 'MULTISELECT', label: '多选' },
  ]},
  { group: '其他', types: [
    { type: 'MEMBERS', label: '人员' }, { type: 'TABLE', label: '表格' },
    { type: 'FILE', label: '附件' }, { type: 'RICHTEXT', label: '富文本' },
    { type: 'CASCADE', label: '级联' },
  ]},
  { group: '布局', types: [
    { type: 'SECTION', label: '分组' },
  ]},
])

const FIELD_LABELS: Record<string, string> = {
  STRING: '文本', TEXT: '多行', INT: '数字', DATE: '日期', DATETIME: '时间',
  SELECT: '下拉', RADIO: '单选', CHECKBOX: '复选', MULTISELECT: '多选',
  MEMBERS: '人员', TABLE: '表格', FILE: '附件', RICHTEXT: '富文', CASCADE: '级联',
}
function typeLabel(t: string) { return FIELD_LABELS[t] || t }

let keyCounter = Date.now()
function createDefaultField(type: string): Field {
  keyCounter++
  const key = `field_${keyCounter}`
  const defs: Record<string, Partial<Field>> = {
    STRING: { name: '单行文本', placeholder: '请输入' },
    TEXT: { name: '多行文本', placeholder: '请输入' },
    INT: { name: '整数' },
    DATE: { name: '日期' },
    DATETIME: { name: '日期时间' },
    SELECT: { name: '下拉选择', choice: [{ label: '选项A', value: 'A' }] },
    RADIO: { name: '单选', choice: [{ label: '是', value: 'yes' }, { label: '否', value: 'no' }] },
    CHECKBOX: { name: '复选框', choice: [{ label: '选项A', value: 'A' }, { label: '选项B', value: 'B' }] },
    MULTISELECT: { name: '多选', choice: [{ label: '选项A', value: 'A' }] },
    MEMBERS: { name: '人员选择' },
    TABLE: { name: '子表格' },
    FILE: { name: '附件' },
    RICHTEXT: { name: '富文本' },
    CASCADE: { name: '级联' },
    SECTION: { name: '新分组' },
  }
  return { key, type, required: false, layout: 'COL_12', ...(defs[type] || {}), show_conditions: {} }
}

function showChoicesEditor(type: string) {
  return ['SELECT', 'RADIO', 'CHECKBOX', 'MULTISELECT'].includes(type)
}

function addSection() {
  localFields.value.push(createDefaultField('SECTION'))
  selectedIndex.value = localFields.value.length - 1
}

function addChoice() {
  if (selectedField.value && selectedField.value.type) {
    if (!selectedField.value.choice) selectedField.value.choice = []
    selectedField.value.choice.push({ label: '', value: '' })
  }
}

function selectField(index: number) {
  selectedIndex.value = index
  const f = localFields.value[index]
  showConditionEnabled.value = !!(f.show_conditions?.field)
}

function onCopyField(index: number) {
  const copy = JSON.parse(JSON.stringify(localFields.value[index]))
  copy.key = `field_${Date.now()}`
  localFields.value.splice(index + 1, 0, copy)
}

function layoutClass(layout: string) {
  return 'fd-layout-' + (layout || 'COL_12').toLowerCase().replace('col_', '')
}
function onSortChange() {
  // Re-index sort_order after drag
  localFields.value.forEach((f, i) => { f.sort_order = i })
}
</script>

<style scoped>
.fd-wrap { display: flex; height: 560px; border: 1px solid #e4e7ed; border-radius: 6px; overflow: hidden; }

/* Left toolbox */
.fd-toolbox { width: 140px; flex-shrink: 0; border-right: 1px solid #e4e7ed; background: #fafafa; padding: 8px; overflow-y: auto; }
.fd-toolbox-title { font-size: 12px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.fd-tg { margin-bottom: 12px; }
.fd-tg-label { font-size: 11px; color: #909399; margin-bottom: 4px; padding-left: 2px; }
.fd-tg-list { display: flex; flex-direction: column; gap: 3px; }
.fd-tg-item { padding: 5px 8px; background: #fff; border: 1px solid #e4e7ed; border-radius: 4px; font-size: 12px; color: #606266; cursor: grab; transition: all 0.15s; text-align: center; }
.fd-tg-item:hover { border-color: #409EFF; color: #409EFF; background: #ecf5ff; }
.fd-tg-item:active { cursor: grabbing; }

/* Canvas */
.fd-canvas { flex: 1; display: flex; flex-direction: column; background: #fff; overflow: hidden; }
.fd-canvas-title { font-size: 12px; font-weight: 600; color: #303133; padding: 8px 12px; border-bottom: 1px solid #e4e7ed; background: #f5f7fa; flex-shrink: 0; display: flex; align-items: center; justify-content: space-between; }
.fd-canvas-actions { display: flex; align-items: center; gap: 8px; }
.fd-col-label { font-size: 11px; color: #909399; }
.fd-col-btns { display: flex; gap: 2px; }
.fd-col-btn { width: 28px; height: 20px; border: 1px solid #dcdfe6; border-radius: 3px; background: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 2px; padding: 0 4px; }
.fd-col-btn:hover { border-color: #409EFF; }
.fd-col-btn.active { border-color: #409EFF; background: #ecf5ff; }
.fd-col-dot { width: 3px; height: 10px; background: #c0c4cc; border-radius: 1px; }
.fd-col-btn.active .fd-col-dot { background: #409EFF; }
.fd-col-divider { width: 1px; height: 16px; background: #e4e7ed; }
.fd-canvas-body { flex: 1; overflow-y: auto; padding: 12px; }
.fd-canvas-empty { text-align: center; color: #C0C4CC; font-size: 13px; padding: 60px 20px; border: 2px dashed #e4e7ed; border-radius: 8px; }
.fd-drag-list { min-height: 200px; display: flex; flex-wrap: wrap; gap: 8px; align-content: flex-start; }
.fd-field-wrap { position: relative; border: 2px solid transparent; border-radius: 6px; padding: 8px; transition: border-color 0.2s; background: #fff; cursor: pointer; }
.fd-field-wrap:hover { border-color: #d9ecff; }
.fd-field-wrap.fd-selected { border-color: #409EFF; box-shadow: 0 0 0 2px rgba(64,158,255,0.15); }
.fd-field-wrap.fd-sec-wrap { border: none; padding: 4px 0; cursor: default; }
.fd-layout-12 { width: 100%; }
.fd-layout-8 { width: calc(66.66% - 6px); }
.fd-layout-6 { width: calc(50% - 4px); }
.fd-layout-4 { width: calc(33.33% - 6px); }
.fd-layout-3 { width: calc(25% - 6px); }
.fd-field-label { font-size: 12px; color: #606266; margin-bottom: 4px; display: flex; align-items: center; gap: 4px; }
.fd-req { color: #F56C6C; }
.fd-field-type-tag { font-size: 10px; color: #909399; background: #f5f7fa; padding: 0 6px; border-radius: 3px; line-height: 16px; }
.fd-placeholder { border: 1px dashed #d9ecff; border-radius: 4px; padding: 8px; font-size: 12px; color: #909399; text-align: center; background: #fafafa; }
.fd-rich { min-height: 48px; }
.fd-actions { position: absolute; top: 4px; right: 4px; display: none; gap: 2px; }
.fd-field-wrap:hover .fd-actions { display: flex; }
.fd-actions :deep(.el-button) { padding: 2px 4px; min-height: 0; }
.fd-add-sec { text-align: center; padding: 6px 0; font-size: 12px; color: #409EFF; cursor: pointer; border: 1px dashed #d9ecff; border-radius: 4px; margin-top: 4px; width: 100%; }
.fd-add-sec:hover { background: #ecf5ff; }

/* Section */
.fd-sec { display: flex; align-items: center; gap: 8px; width: 100%; padding: 4px 0; }
.fd-sec-title { font-size: 13px; font-weight: 600; color: #303133; white-space: nowrap; display: flex; align-items: center; gap: 4px; }
.fd-sec-line { flex: 1; height: 1px; background: #e4e7ed; }

/* Right properties */
.fd-props { width: 260px; flex-shrink: 0; border-left: 1px solid #e4e7ed; background: #fafafa; padding: 12px; overflow-y: auto; }
.fd-props-title { font-size: 12px; font-weight: 600; color: #303133; margin-bottom: 12px; }
.fd-props-empty { display: flex; align-items: center; justify-content: center; }
.fd-choices { border-top: 1px solid #e4e7ed; padding-top: 12px; margin-top: 4px; }
.fd-choices-title { font-size: 12px; font-weight: 600; color: #606266; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
.fd-choice-row { display: flex; align-items: center; margin-bottom: 4px; }
.fd-choices-empty { font-size: 11px; color: #C0C4CC; padding: 4px 0; }

/* Footer */
.fd-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 8px 12px; border-top: 1px solid #e4e7ed; background: #fafafa; }
</style>
