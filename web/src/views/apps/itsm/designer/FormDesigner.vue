<template>
  <div class="fd-wrap">
    <!-- Left: Toolbox -->
    <div class="fd-toolbox" v-if="!previewMode">
      <div class="fd-toolbox-title">{{ $t('message.formDesigner.toolbox') }}</div>
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
        <span>{{ previewMode ? $t('message.formDesigner.preview') : $t('message.formDesigner.design') }}</span>
        <div class="fd-canvas-actions">
          <!-- Global column selector (design mode only) -->
          <template v-if="!previewMode">
            <span class="fd-col-label">{{ $t('message.formDesigner.columnLabel') }}</span>
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
            {{ previewMode ? $t('message.formDesigner.exitPreview') : $t('message.formDesigner.preview') }}
          </el-button>
        </div>
      </div>
      <div class="fd-canvas-body">
        <div v-if="!localFields.length" class="fd-canvas-empty">
          {{ $t('message.formDesigner.empty') }}
        </div>
        <!-- Preview mode: use shared ItsmFormRenderer -->
        <ItsmFormRenderer
          v-if="previewMode && localFields.length"
          mode="preview"
          :fields="localFields"
          :show-submit="false"
        />
        <!-- Design mode: VueDraggable wraps ItsmFormField for per-field drag + actions -->
        <VueDraggable v-else-if="!previewMode" v-model="localFields" group="form-fields" item-key="key" class="fd-drag-list"
          @change="onSortChange">
          <template #item="{ element, index }">
            <ItsmFormField
              :field="element"
              :mode="'design'"
              :selected="selectedIndex === index"
              :show-type-tag="true"
              :show-actions="true"
              @select="selectField(index)"
              @copy="onCopyField(index)"
              @delete="localFields.splice(index, 1)"
            />
          </template>
        </VueDraggable>
        <div v-if="!previewMode" class="fd-add-sec" @click="addSection">{{ $t('message.formDesigner.addSection') }}</div>
      </div>
    </div>

    <!-- Right: Property panel -->
    <div class="fd-props" v-if="selectedField && !previewMode">
      <div class="fd-props-title">{{ $t('message.formDesigner.fieldProps') }}</div>
      <el-form size="small" label-position="top">
        <template v-if="selectedField.type !== 'SECTION'">
          <el-form-item :label="$t('message.formDesigner.key')">
            <el-input v-model="selectedField.key" />
          </el-form-item>
          <el-form-item :label="$t('message.formDesigner.name')">
            <el-input v-model="selectedField.name" />
          </el-form-item>
          <el-form-item :label="$t('message.formDesigner.placeholder')">
            <el-input v-model="selectedField.placeholder" :placeholder="$t('message.formDesigner.optionalPlaceholder')" />
          </el-form-item>
          <el-form-item :label="$t('message.formDesigner.required')">
            <el-switch v-model="selectedField.required" />
          </el-form-item>
          <el-form-item :label="$t('message.formDesigner.layout')">
            <el-radio-group v-model="selectedField.layout">
              <el-radio value="COL_12">{{ $t('message.formDesigner.colFull') }}</el-radio>
              <el-radio value="COL_8">{{ $t('message.formDesigner.colTwoThirds') }}</el-radio>
              <el-radio value="COL_6">{{ $t('message.formDesigner.colHalf') }}</el-radio>
              <el-radio value="COL_4">{{ $t('message.formDesigner.colOneThird') }}</el-radio>
              <el-radio value="COL_3">{{ $t('message.formDesigner.colQuarter') }}</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item :label="$t('message.formDesigner.defaultValue')">
            <el-input v-if="['STRING','TEXT'].includes(selectedField.type)" v-model="selectedField.default" />
            <el-select v-else-if="['SELECT','RADIO','MULTISELECT'].includes(selectedField.type)" v-model="selectedField.default" clearable size="small" style="width:100%">
              <el-option v-for="c in selectedField.choice || []" :key="c.value" :label="c.label" :value="c.value" />
            </el-select>
            <el-checkbox-group v-else-if="selectedField.type === 'CHECKBOX'" v-model="selectedField.default" size="small">
              <el-checkbox v-for="c in selectedField.choice || []" :key="c.value" :label="c.value">{{ c.label }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item :label="$t('message.formDesigner.sectionLabel')">
            <el-input v-model="selectedField.name" :placeholder="$t('message.formDesigner.sectionPlaceholder')" />
          </el-form-item>
        </template>

        <!-- Choices editor (SELECT/RADIO/CHECKBOX/MULTISELECT) -->
        <div v-if="showChoicesEditor(selectedField.type)" class="fd-choices">
          <!-- Source toggle: manual vs preset -->
          <div class="fd-choices-source">
            <label class="fd-radio-label" :class="{ active: !selectedField._usePreset }" @click="setSourceMode(false)">
              {{ $t('message.formDesigner.manualInput') }}
            </label>
            <label class="fd-radio-label" :class="{ active: selectedField._usePreset }" @click="setSourceMode(true)">
              {{ $t('message.formDesigner.fromPreset') }}
            </label>
          </div>

          <!-- Preset mode: dropdown + preview + default value -->
          <div v-if="selectedField._usePreset" class="fd-preset-select">
            <el-select v-model="selectedField.preset_id" filterable clearable size="small" style="width:100%"
              :placeholder="$t('message.preset.selectPreset')" @change="onPresetChange">
              <el-option v-for="p in presetOptions" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <!-- Preview loaded options -->
            <div v-if="selectedField.choice?.length" class="fd-preset-preview">
              <div style="font-size:11px;color:#67C23A;margin-bottom:4px">
                ✓ {{ $t('message.formDesigner.presetLoaded', { n: selectedField.choice.length }) }}
              </div>
              <div v-for="(c, ci) in selectedField.choice" :key="ci" class="fd-preset-option">
                <span class="fd-preset-option-label">{{ c.label }}</span>
                <span class="fd-preset-option-value">{{ c.value }}</span>
              </div>
            </div>
          </div>

          <!-- Manual mode: existing choice rows -->
          <template v-else>
            <div class="fd-choices-title">{{ $t('message.formDesigner.choices') }}
              <el-button size="small" text @click="addChoice">{{ $t('message.formDesigner.addChoice') }}</el-button>
            </div>
            <div v-for="(c, ci) in selectedField.choice" :key="ci" class="fd-choice-row">
              <el-input v-model="c.label" size="small" :placeholder="$t('message.formDesigner.dispName')" style="flex:1" />
              <el-input v-model="c.value" size="small" :placeholder="$t('message.formDesigner.value')" style="flex:1;margin:0 4px" />
              <el-button size="small" text type="danger" @click="selectedField.choice.splice(ci, 1)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div v-if="!selectedField.choice?.length" class="fd-choices-empty">{{ $t('message.formDesigner.noChoice') }}</div>
          </template>
        </div>

        <!-- Show condition -->
        <el-form-item :label="$t('message.formDesigner.showCondition')">
          <el-switch v-model="showConditionEnabled" />
        </el-form-item>
        <template v-if="showConditionEnabled">
          <el-form-item :label="$t('message.formDesigner.conditionField')">
            <el-select v-model="selectedField.show_conditions.field" filterable style="width:100%">
              <el-option v-for="f in availableConditionFields" :key="f.key" :label="f.name || f.key" :value="f.key" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('message.formDesigner.conditionValue')">
            <el-input v-model="selectedField.show_conditions.value" :placeholder="$t('message.formDesigner.equalPlaceholder')" />
          </el-form-item>
        </template>
      </el-form>
    </div>
    <div v-else-if="!previewMode" class="fd-props fd-props-empty">
      <span style="color:#C0C4CC">{{ $t('message.formDesigner.clickProp') }}</span>
    </div>
  </div>
  <div class="fd-footer">
    <el-button @click="emit('cancel')">{{ $t('message.common.cancel') }}</el-button>
    <el-button type="primary" @click="emit('save', localFields)">{{ $t('message.formDesigner.save') }}</el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Delete, CopyDocument, FolderOpened } from '@element-plus/icons-vue'
import VueDraggable from 'vuedraggable'
import ItsmFormRenderer from '/@/components/ItsmFormRenderer/index.vue'
import ItsmFormField from '/@/components/ItsmFormRenderer/ItsmFormField.vue'
import { presetApi } from '/@/api/itsm/index'

const { t } = useI18n()

const props = defineProps<{ fields?: any[] }>()
const emit = defineEmits<{ save: [fields: any[]]; cancel: [] }>()

interface Field { key: string; name?: string; type: string; required: boolean; layout: string; choice?: any[]; default?: any; placeholder?: string; sort_order?: number; show_conditions?: any; _usePreset?: boolean; preset_id?: number | null }

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

// Initialize _usePreset on all fields when loading from props
watch(() => props.fields, (f) => {
  localFields.value = f ? JSON.parse(JSON.stringify(f)) : []
  // Ensure backward compat: init _usePreset for loaded fields with preset_id
  localFields.value.forEach(field => {
    if (field._usePreset == null) field._usePreset = field.preset_id != null
  })
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
  // Ensure _usePreset is initialized on every field (handles both new and loaded fields)
  if (f) {
    if (f._usePreset == null) f._usePreset = f.preset_id != null
  }
}

function onCopyField(index: number) {
  const copy = JSON.parse(JSON.stringify(localFields.value[index]))
  copy.key = `field_${Date.now()}`
  localFields.value.splice(index + 1, 0, copy)
}

function onSortChange() {
  // Re-index sort_order after drag
  localFields.value.forEach((f, i) => { f.sort_order = i })
}

// ── 预设选项加载 ──
const presetOptions = ref<any[]>([])

async function loadPresets() {
  try {
    const res = await presetApi.list({ preset_type: 'options', page_size: 200 })
    presetOptions.value = (res as any).data || []
  } catch { presetOptions.value = [] }
}

function setSourceMode(usePreset: boolean) {
  if (!selectedField.value) return
  selectedField.value._usePreset = usePreset
  if (usePreset) {
    // Switching to preset: keep existing choice for fallback
  } else {
    // Switching to manual: clear preset reference, keep current choice
    selectedField.value.preset_id = null
  }
}

function onPresetChange(presetId: number | null) {
  if (!selectedField.value) return
  // Clear stale default when choice options change
  selectedField.value.default = undefined
  if (presetId) {
    const preset = presetOptions.value.find((p: any) => p.id === presetId)
    if (preset && preset.value) {
      selectedField.value.choice = JSON.parse(JSON.stringify(preset.value))
      selectedField.value.preset_id = presetId
    }
  } else {
    selectedField.value.preset_id = null
    selectedField.value.choice = []
  }
}

onMounted(() => { loadPresets() })
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
.fd-add-sec { text-align: center; padding: 6px 0; font-size: 12px; color: #409EFF; cursor: pointer; border: 1px dashed #d9ecff; border-radius: 4px; margin-top: 4px; width: 100%; }
.fd-add-sec:hover { background: #ecf5ff; }

/* Right properties */
.fd-props { width: 260px; flex-shrink: 0; border-left: 1px solid #e4e7ed; background: #fafafa; padding: 12px; overflow-y: auto; }
.fd-props-title { font-size: 12px; font-weight: 600; color: #303133; margin-bottom: 12px; }
.fd-props-empty { display: flex; align-items: center; justify-content: center; }
.fd-choices { border-top: 1px solid #e4e7ed; padding-top: 12px; margin-top: 4px; }
.fd-choices-source { display: flex; gap: 0; margin-bottom: 10px; border-radius: 4px; overflow: hidden; border: 1px solid #dcdfe6; }
.fd-radio-label { flex: 1; text-align: center; padding: 4px 0; font-size: 12px; cursor: pointer; background: #f5f7fa; color: #909399; transition: all 0.2s; }
.fd-radio-label.active { background: #ecf5ff; color: #409EFF; font-weight: 600; }
.fd-radio-label:hover:not(.active) { color: #606266; }
.fd-preset-select { margin-bottom: 8px; }
.fd-preset-preview { margin-top: 8px; padding: 8px; background: #f0f9eb; border-radius: 4px; }
.fd-preset-option { display: flex; gap: 8px; font-size: 11px; padding: 2px 0; }
.fd-preset-option-label { color: #606266; min-width: 60px; }
.fd-preset-option-value { color: #909399; font-family: monospace; }
.fd-choices-title { font-size: 12px; font-weight: 600; color: #606266; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
.fd-choice-row { display: flex; align-items: center; margin-bottom: 4px; }
.fd-choices-empty { font-size: 11px; color: #C0C4CC; padding: 4px 0; }

/* Footer */
.fd-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 8px 12px; border-top: 1px solid #e4e7ed; background: #fafafa; }
</style>
