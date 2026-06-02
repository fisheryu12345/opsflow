<template>
  <el-dialog v-model="visible" title="Manage Execution Schemes" width="600px" @close="loadSchemes">
    <div class="scheme-manager">
      <div class="scheme-header">
        <el-button size="small" type="primary" :icon="Plus" @click="showEditor = true; editForm = { name: '', description: '', excluded_nodes: [], variable_overrides: {}, is_default: false }">
          New Scheme
        </el-button>
      </div>
      <el-table :data="schemes" size="small" empty-text="No execution schemes defined">
        <el-table-column prop="name" label="Name" min-width="140" />
        <el-table-column prop="description" label="Desc" min-width="180" show-overflow-tooltip />
        <el-table-column label="Default" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success" size="small">Default</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="140" align="center">
          <template #default="{ row }">
            <el-button size="small" text @click="editScheme(row)">Edit</el-button>
            <el-button size="small" text type="danger" @click="deleteScheme(row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Edit Dialog -->
      <el-dialog v-model="showEditor" title="Edit Scheme" width="420px" append-to-body destroy-on-close>
        <el-form :model="editForm" label-width="100px" size="small">
          <el-form-item label="Name" required>
            <el-input v-model="editForm.name" placeholder="e.g. Quick Check" />
          </el-form-item>
          <el-form-item label="Desc">
            <el-input v-model="editForm.description" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="Default">
            <el-switch v-model="editForm.is_default" />
          </el-form-item>
          <el-form-item label="Excluded Nodes">
            <el-input v-model="excludedText" type="textarea" :rows="3"
              placeholder="Comma-separated node IDs, e.g. node_2, node_5" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button size="small" @click="showEditor = false">Cancel</el-button>
          <el-button size="small" type="primary" @click="saveScheme">Save</el-button>
        </template>
      </el-dialog>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { GetSchemes, CreateScheme, UpdateScheme, DeleteScheme } from '/@/api/opsflow/templates'

const props = defineProps<{ templateId: number | null; visible: boolean }>()
const emit = defineEmits(['update:visible', 'updated'])

const schemes = ref<any[]>([])
const showEditor = ref(false)
const editForm = ref<any>({ name: '', description: '', excluded_nodes: [], variable_overrides: {}, is_default: false })
const editingId = ref<number | null>(null)

const excludedText = computed({
  get: () => (editForm.value.excluded_nodes || []).join(', '),
  set: (val: string) => { editForm.value.excluded_nodes = val.split(',').map((s: string) => s.trim()).filter(Boolean) },
})

async function loadSchemes() {
  if (!props.templateId) { schemes.value = []; return }
  try {
    const res = await GetSchemes(props.templateId)
    schemes.value = res.data?.data || res.data || []
  } catch { schemes.value = [] }
}

function editScheme(row: any) {
  editingId.value = row.id
  editForm.value = { ...row }
  showEditor.value = true
}

async function saveScheme() {
  if (!props.templateId) return
  try {
    if (editingId.value) {
      await UpdateScheme(props.templateId, editingId.value, editForm.value)
    } else {
      await CreateScheme(props.templateId, editForm.value)
    }
    ElMessage.success('Scheme saved')
    showEditor.value = false
    editingId.value = null
    loadSchemes()
    emit('updated')
  } catch { ElMessage.error('Failed to save scheme') }
}

async function deleteScheme(row: any) {
  if (!props.templateId) return
  try {
    await ElMessageBox.confirm(`Delete scheme "${row.name}"?`, 'Confirm', { type: 'warning' })
    await DeleteScheme(props.templateId, row.id)
    ElMessage.success('Scheme deleted')
    loadSchemes()
    emit('updated')
  } catch { /* cancelled */ }
}

watch(() => props.visible, (v) => { if (v) loadSchemes() })
</script>

<style lang="scss" scoped>
@import '../styles/opsflow-global';

.scheme-manager { min-height: 200px; }
.scheme-header { margin-bottom: 12px; }
</style>
