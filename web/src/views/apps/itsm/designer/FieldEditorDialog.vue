<template>
  <div class="field-editor">
    <div class="fe-toolbar">
      <el-select v-model="newFieldType" size="small" style="width:130px;margin-right:6px;">
        <el-option v-for="ft in fieldTypes" :key="ft.value" :label="ft.label" :value="ft.value" />
      </el-select>
      <el-input v-model="newFieldKey" size="small" :placeholder="$t('message.formDesigner.key')" style="width:100px;margin-right:6px;" />
      <el-input v-model="newFieldName" size="small" :placeholder="$t('message.formDesigner.name')" style="width:120px;margin-right:6px;" />
      <el-button size="small" type="primary" @click="onAddField">{{ $t('message.designer.addField') }}</el-button>
    </div>
    <div class="fe-list" v-if="localFields.length">
      <div v-for="(f, fi) in localFields" :key="fi" class="fe-item">
        <div class="fe-info">
          <span class="fe-name">{{ f.name }}</span>
          <span class="fe-key">{{ f.key }}</span>
          <el-tag size="small">{{ f.type }}</el-tag>
          <el-tag v-if="f.required" size="small" type="danger">{{ $t('message.formDesigner.required') }}</el-tag>
        </div>
        <div class="fe-actions">
          <el-button v-if="showChoiceEditor(f.type)" size="small" text @click="editChoices(f, fi)">
            <el-icon><Setting /></el-icon>
          </el-button>
          <el-button size="small" text type="danger" @click="localFields.splice(fi, 1)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
    <div v-else class="fe-empty">{{ $t('message.formDesigner.noFieldClickAdd') }}</div>

    <!-- Choices editor -->
    <div v-if="editingChoices" class="fe-choices">
      <div class="fe-choices-title">{{ $t('message.formDesigner.editChoices', { name: editingChoicesName }) }}</div>
      <div v-for="(c, ci) in editingChoicesList" :key="ci" class="fe-choice-row">
        <el-input v-model="c.label" size="small" :placeholder="$t('message.formDesigner.dispName')" style="width:130px;margin-right:4px;" />
        <el-input v-model="c.value" size="small" :placeholder="$t('message.formDesigner.value')" style="width:110px;margin-right:4px;" />
        <el-button size="small" text type="danger" @click="editingChoicesList.splice(ci, 1)">
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
      <el-button size="small" @click="editingChoicesList.push({ label: '', value: '' })">{{ $t('message.formDesigner.addChoice') }}</el-button>
      <el-button size="small" type="primary" @click="saveChoices">{{ $t('message.formDesigner.complete') }}</el-button>
    </div>

    <div style="margin-top:12px;">
      <el-button @click="$emit('save', localFields)" type="primary">{{ $t('message.formDesigner.save') }}</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Delete, Setting } from '@element-plus/icons-vue'

const { t } = useI18n()
const props = defineProps<{ fields?: any[] }>()
const emit = defineEmits<{ save: [fields: any[]] }>()

const localFields = ref<any[]>(props.fields ? JSON.parse(JSON.stringify(props.fields)) : [])
const newFieldType = ref('STRING')
const newFieldKey = ref('')
const newFieldName = ref('')
const editingChoices = ref(false)
const editingChoicesName = ref('')
const editingChoicesList = ref<any[]>([])
const editingFieldIndex = ref(-1)

const fieldTypes = [
  { label: '单行文本', value: 'STRING' }, { label: '多行文本', value: 'TEXT' },
  { label: '整数', value: 'INT' }, { label: '日期', value: 'DATE' },
  { label: '日期时间', value: 'DATETIME' }, { label: '下拉选择', value: 'SELECT' },
  { label: '单选', value: 'RADIO' }, { label: '复选框', value: 'CHECKBOX' },
  { label: '多选', value: 'MULTISELECT' }, { label: '人员', value: 'MEMBERS' },
  { label: '表格', value: 'TABLE' }, { label: '附件', value: 'FILE' },
  { label: '富文本', value: 'RICHTEXT' }, { label: '级联', value: 'CASCADE' },
]

function showChoiceEditor(type: string) { return ['SELECT', 'RADIO', 'CHECKBOX', 'MULTISELECT'].includes(type) }
function onAddField() {
  if (!newFieldKey.value || !newFieldName.value) return
  localFields.value.push({ key: newFieldKey.value, name: newFieldName.value, type: newFieldType.value, required: false, layout: 'COL_12', choice: showChoiceEditor(newFieldType.value) ? [] : undefined })
  newFieldKey.value = ''
  newFieldName.value = ''
}
function editChoices(f: any, fi: number) {
  editingChoicesName.value = f.name
  editingChoicesList.value = (f.choice || []).map((c: any) => ({ ...c }))
  editingFieldIndex.value = fi
  editingChoices.value = true
}
function saveChoices() {
  if (editingFieldIndex.value >= 0) localFields.value[editingFieldIndex.value].choice = editingChoicesList.value.map(c => ({ ...c }))
  editingChoices.value = false
}
</script>

<style scoped>
.field-editor { padding: 4px 0; }
.fe-toolbar { display: flex; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 4px; }
.fe-list { display: flex; flex-direction: column; gap: 4px; }
.fe-item { display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; border: 1px solid #ebeef5; border-radius: 6px; background: #fafafa; }
.fe-info { display: flex; align-items: center; gap: 6px; }
.fe-name { font-weight: 600; color: #303133; font-size: 13px; }
.fe-key { color: #909399; font-size: 11px; font-family: monospace; }
.fe-actions { display: flex; gap: 4px; }
.fe-empty { color: #C0C4CC; padding: 20px 0; text-align: center; font-size: 13px; }
.fe-choices { margin-top: 16px; padding: 12px; background: #f5f7fa; border-radius: 6px; }
.fe-choices-title { font-weight: 600; font-size: 13px; margin-bottom: 8px; color: #606266; }
.fe-choice-row { display: flex; align-items: center; margin-bottom: 4px; }
</style>
