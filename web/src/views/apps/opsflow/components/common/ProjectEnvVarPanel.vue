<template>
  <div class="env-panel">
    <div class="env-header">
      <span class="env-title">{{ $t("message.opsflowPage.envTitle") }}</span>
      <el-button size="small" type="primary" :icon="Plus" @click="showForm(null)">{{ $t("message.opsflowPage.envAdd") }}</el-button>
    </div>
    <p class="env-desc">{{ $t("message.opsflowPage.envDesc") }}</p>

    <el-input v-model="search" :placeholder="$t('message.opsflowPage.envSearch')" clearable size="small" prefix-icon="Search" class="env-search" />

    <div v-if="loading" v-loading="loading" style="min-height: 80px" />

    <div v-else-if="filteredList.length === 0" class="env-empty">
      <el-empty :description="search ? t('message.opsflowPage.envNoMatch') : t('message.opsflowPage.envNoVars')" :image-size="40" />
    </div>

    <div v-else class="env-list">
      <div v-for="item in filteredList" :key="item.key" class="env-row" :class="{ 'is-pwd': item.var_type === 'password' }">
        <div class="env-row-main">
          <div class="env-row-key">
            <span class="env-key">{{ item.key }}</span>
            <el-tag size="small" effect="plain" class="env-type-tag">{{ typeLabel(item.var_type) }}</el-tag>
          </div>
          <div class="env-row-value">
            <span v-if="item.var_type === 'password' && !item._revealed" class="env-masked">••••••••</span>
            <span v-else class="env-value-text">{{ item.value || '—' }}</span>
          </div>
          <div class="env-row-desc" v-if="item.description">{{ item.description }}</div>
        </div>
        <div class="env-row-actions">
          <el-tooltip content="Edit" placement="top">
            <el-button size="small" text :icon="Edit" @click="showForm(item)" />
          </el-tooltip>
          <el-tooltip content="Toggle reveal" placement="top" v-if="item.var_type === 'password'">
            <el-button size="small" text :icon="item._revealed ? Hide : View" @click="item._revealed = !item._revealed" />
          </el-tooltip>
          <el-popconfirm title="Delete this variable?" @confirm="handleDelete(item)">
            <template #reference>
              <el-button size="small" text type="danger" :icon="Delete" />
            </template>
          </el-popconfirm>
        </div>
      </div>
    </div>

    <!-- Form dialog -->
    <el-dialog v-model="formVisible" :title="editing ? $t('message.opsflowPage.envEditVar') : $t('message.opsflowPage.envAddVar')" width="480px" top="12vh" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item :label="$t('message.opsflowPage.envFormKey')" required>
          <el-input v-model="form.key" :disabled="!!editing" :placeholder="$t('message.opsflowPage.envFormKeyPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('message.opsflowPage.envFormType')">
          <el-select v-model="form.var_type" style="width:100%">
            <el-option :label="$t('message.opsflowPage.envTypeText')" value="input" />
            <el-option :label="$t('message.opsflowPage.envTypeTextarea')" value="textarea" />
            <el-option :label="$t('message.opsflowPage.envTypePassword')" value="password" />
            <el-option :label="$t('message.opsflowPage.envTypeNumber')" value="int" />
            <el-option :label="$t('message.opsflowPage.envTypeFloat')" value="float" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.opsflowPage.envFormValue')">
          <el-input v-model="form.value" :type="form.var_type === 'password' ? 'password' : 'text'" :rows="form.var_type === 'textarea' ? 3 : 1" />
        </el-form-item>
        <el-form-item :label="$t('message.opsflowPage.envFormDesc')">
          <el-input v-model="form.description" :placeholder="$t('message.opsflowPage.envFormDescPlaceholder')" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button  @click="formVisible = false">{{ $t("message.common.cancel") }}</el-button>
        <el-button  type="primary" @click="handleSave" :loading="saving">{{ $t("message.common.save") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete, View, Hide } from '@element-plus/icons-vue'
import { GetProjectEnvVars, SetProjectEnvVars, PatchProjectEnvVars } from '../../api/projects'

interface EnvVarItem {
  id?: number
  key: string
  value: string
  var_type: string
  description: string
  _revealed?: boolean
}

const { t } = useI18n()

const props = defineProps<{ projectId: number | null }>()

const items = ref<EnvVarItem[]>([])
const loading = ref(false)
const saving = ref(false)
const search = ref('')
const formVisible = ref(false)
const editing = ref<EnvVarItem | null>(null)
const form = ref({ key: '', value: '', var_type: 'input', description: '' })

const filteredList = computed(() => {
  if (!search.value) return items.value
  const q = search.value.toLowerCase()
  return items.value.filter(i => i.key.toLowerCase().includes(q) || i.description.toLowerCase().includes(q))
})

function typeLabel(type: string) {
  const m: Record<string, string> = { input: t('message.opsflowPage.envTypeText'), textarea: t('message.opsflowPage.envTypeTextarea'), password: t('message.opsflowPage.envTypePassword'), int: t('message.opsflowPage.envTypeNumber'), float: t('message.opsflowPage.envTypeFloat') }
  return m[type] || type
}

function showForm(item: EnvVarItem | null) {
  if (item) {
    editing.value = item
    form.value = { key: item.key, value: '', var_type: item.var_type, description: item.description || '' }
  } else {
    editing.value = null
    form.value = { key: '', value: '', var_type: 'input', description: '' }
  }
  formVisible.value = true
}

async function load() {
  if (!props.projectId) return
  loading.value = true
  try {
    const res: any = await GetProjectEnvVars(props.projectId)
    items.value = ((res as any).data || []).map((v: any) => ({ ...v, _revealed: false }))
  } catch { items.value = [] }
  loading.value = false
}

async function handleSave() {
  if (!form.value.key) { ElMessage.warning('Key is required'); return }
  saving.value = true
  try {
    if (editing.value) {
      await PatchProjectEnvVars(props.projectId!, [form.value])
      ElMessage.success('Variable updated')
    } else {
      // Check for duplicate
      if (items.value.find(i => i.key === form.value.key)) {
        ElMessage.warning('Key already exists')
        saving.value = false
        return
      }
      await PatchProjectEnvVars(props.projectId!, [form.value])
      ElMessage.success('Variable added')
    }
    formVisible.value = false
    await load()
  } catch (e: any) { ElMessage.error(e?.msg || 'Save failed') }
  saving.value = false
}

async function handleDelete(item: EnvVarItem) {
  try {
    await SetProjectEnvVars(props.projectId!, items.value.filter(i => i.key !== item.key))
    ElMessage.success('Variable deleted')
    await load()
  } catch (e: any) { ElMessage.error(e?.msg || 'Delete failed') }
}

watch(() => props.projectId, (v) => { if (v) load() }, { immediate: true })
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;
.env-panel { display: flex; flex-direction: column; gap: 12px; }
.env-header { display: flex; align-items: center; justify-content: space-between; }
.env-title { font-size: 14px; font-weight: 600; color: #303133; }
.env-desc { margin: 0; font-size: 12px; color: #909399; line-height: 1.6; }
.env-desc code { background: #f5f7fa; padding: 1px 5px; border-radius: 3px; font-size: 11px; color: #E6A23C; }
.env-search { width: 100%; }
.env-empty { padding: 20px 0; }
.env-list { display: flex; flex-direction: column; gap: 6px; max-height: 400px; overflow-y: auto; }
.env-row { display: flex; justify-content: space-between; align-items: flex-start; padding: 10px 12px; border: 1px solid #f0f0f0; border-radius: 8px; transition: all 0.15s; }
.env-row:hover { background: #fafcff; border-color: #dcdfe6; }
.env-row.is-pwd { border-color: #fdf6ec; background: #fffcf0; }
.env-row-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.env-row-key { display: flex; align-items: center; gap: 8px; }
.env-key { font-size: 13px; font-weight: 600; color: #303133; font-family: monospace; }
.env-type-tag { font-size: 10px; }
.env-row-value { font-size: 13px; color: #606266; }
.env-masked { font-size: 16px; letter-spacing: 2px; color: #c0c4cc; }
.env-value-text { word-break: break-all; }
.env-row-desc { font-size: 11px; color: #c0c4cc; }
.env-row-actions { display: flex; gap: 4px; flex-shrink: 0; margin-left: 8px; }
</style>
