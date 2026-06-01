<template>
  <el-dialog :model-value="visible" @update:model-value="emit('update:visible', $event)"
    :title="projectName ? `Plugins: ${projectName}` : 'Plugin Visibility'" width="720px" top="5vh" destroy-on-close
    class="opsflow-dialog pv-dialog">
    <div v-loading="loading" class="pv-body">
      <div class="pv-intro">
        Toggle plugins ON to show them in this project, OFF to hide them.
        <span v-if="enabledCount < totalPlugins" class="pv-intro-note">{{ disabledCount }} plugin(s) currently hidden.</span>
      </div>

      <el-input v-model="searchQuery" placeholder="Search plugin name or code..."
        clearable prefix-icon="Search" size="small" class="pv-search" />

      <div v-for="(plugins, group) in groupedPlugins" :key="group" class="pv-group">
        <div class="pv-group-header">
          <span class="pv-group-name">{{ group }}</span>
          <span class="pv-group-count">{{ plugins.length }}</span>
        </div>
        <div v-for="plugin in plugins" :key="plugin.code" class="pv-row">
          <div class="pv-row-left">
            <div class="pv-row-name">{{ plugin.name }}</div>
            <div class="pv-row-code">{{ plugin.code }}</div>
          </div>
          <div class="pv-row-right">
            <el-switch
              :model-value="plugin.enabled"
              size="small"
              active-text="On"
              inactive-text="Off"
              @change="(val: boolean) => plugin.enabled = val"
            />
          </div>
        </div>
      </div>

      <el-empty v-if="filteredPlugins.length === 0 && !loading"
        description="No plugins found" :image-size="60" />
    </div>

    <template #footer>
      <div class="pv-footer">
        <span class="pv-footer-note">{{ changedCount > 0 ? `${changedCount} change(s) unsaved` : '' }}</span>
        <el-button size="small" @click="handleReset">Reset</el-button>
        <el-button size="small" type="primary" :loading="saving" @click="handleSave"
          :disabled="changedCount === 0">Save</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { GetPluginsVisibilityList, BatchSetPluginsVisibility } from '/@/api/opsflow/plugins'
import { GetProjects } from '/@/api/opsflow/projects'

interface PluginItem {
  code: string
  name: string
  group: string
  description: string
  risk_level: string
  allowed_projects: number[]
  enabled: boolean  // computed: visible for THIS project?
}

const props = withDefaults(defineProps<{
  visible?: boolean
  projectId?: number | null
  projectName?: string
}>(), { visible: false, projectId: null, projectName: '' })

const emit = defineEmits<{ (e: 'update:visible', val: boolean): void }>()

const loading = ref(false)
const saving = ref(false)
const searchQuery = ref('')
const allProjects = ref<{ id: number; name: string }[]>([])
const plugins = ref<PluginItem[]>([])
const originalSnapshot = ref('') // JSON for change detection

const filteredPlugins = computed(() => {
  if (!searchQuery.value) return plugins.value
  const q = searchQuery.value.toLowerCase()
  return plugins.value.filter(p =>
    p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q)
  )
})

const groupedPlugins = computed(() => {
  const map: Record<string, PluginItem[]> = {}
  for (const p of filteredPlugins.value) {
    (map[p.group] ||= []).push(p)
  }
  return map
})

const totalPlugins = computed(() => plugins.value.length)
const enabledCount = computed(() => plugins.value.filter(p => p.enabled).length)
const disabledCount = computed(() => totalPlugins.value - enabledCount.value)

const changedCount = computed(() => {
  const snap = JSON.stringify(plugins.value.map(p => [p.code, p.enabled]))
  return snap !== originalSnapshot.value
    ? plugins.value.filter((p, i) => {
        const orig = JSON.parse(originalSnapshot.value || '[]')
        return p.enabled !== orig[i]?.[1]
      }).length
    : 0
})

async function loadData() {
  if (!props.projectId) return
  loading.value = true
  try {
    const [pluginRes, projectRes] = await Promise.all([
      GetPluginsVisibilityList(),
      GetProjects(),
    ])
    allProjects.value = ((projectRes as any).data || []).filter((p: any) => p.is_active !== false)

    const rawPlugins = pluginRes.data?.data || pluginRes.data || []
    plugins.value = rawPlugins.map((p: any) => {
      const allowed = p.allowed_projects || []
      const enabled = allowed.length === 0 || allowed.includes(props.projectId as number)
      return {
        code: p.code,
        name: p.name,
        group: p.group || 'General',
        description: p.description || '',
        risk_level: p.risk_level || 'low',
        allowed_projects: [...allowed],
        enabled,
      }
    })
    originalSnapshot.value = JSON.stringify(plugins.value.map(p => [p.code, p.enabled]))
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Failed to load')
    plugins.value = []
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!props.projectId) return
  saving.value = true
  try {
    const pid = props.projectId
    const otherIds = allProjects.value
      .filter(p => p.id !== pid)
      .map(p => p.id)

    // Build new allowed_projects per plugin WITHOUT mutating plugins.value
    const newAllowed = new Map<string, number[]>()
    for (const plugin of plugins.value) {
      const wasEnabled = plugin.allowed_projects.length === 0 || plugin.allowed_projects.includes(pid)
      if (plugin.enabled === wasEnabled) continue

      let next: number[]
      if (plugin.enabled) {
        if (plugin.allowed_projects.length === 0) {
          next = [pid, ...otherIds]
        } else if (!plugin.allowed_projects.includes(pid)) {
          next = [...plugin.allowed_projects, pid]
        } else {
          continue
        }
      } else {
        if (plugin.allowed_projects.length === 0) {
          // Was public → restrict to all OTHER projects
          next = otherIds.length > 0 ? [...otherIds] : [-1]
        } else {
          next = plugin.allowed_projects.filter(id => id !== pid)
          // If nothing left, use [-1] sentinel instead of [] ([]=public to backend)
          if (next.length === 0) next = [-1]
        }
      }
      newAllowed.set(plugin.code, next)
    }

    if (newAllowed.size === 0) {
      ElMessage.info('No changes to save')
      saving.value = false
      return
    }

    // Build payload and send as one batch call
    const payload = Array.from(newAllowed.entries()).map(([code, ids]) => ({
      code, project_ids: ids,
    }))
    await BatchSetPluginsVisibility(payload)

    // Apply changes to local state ONLY after successful API call
    for (const plugin of plugins.value) {
      const na = newAllowed.get(plugin.code)
      if (na !== undefined) {
        plugin.allowed_projects = na
      }
    }
    originalSnapshot.value = JSON.stringify(plugins.value.map(p => [p.code, p.enabled]))
    ElMessage.success('Plugin visibility updated')
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || 'Save failed')
  } finally {
    saving.value = false
  }
}

function handleReset() { searchQuery.value = ''; loadData(); ElMessage.info('Changes discarded') }

watch(() => props.visible, (v) => { if (v) { loadData(); searchQuery.value = '' } })
</script>

<style scoped>
.pv-dialog :deep(.el-dialog__body) { padding: 0; }
.pv-body { max-height: 65vh; overflow-y: auto; padding: 18px 20px; }
.pv-intro { font-size: 13px; color: #606266; margin-bottom: 14px; line-height: 1.6; }
.pv-intro-note { color: #E6A23C; font-weight: 500; }
.pv-search { margin-bottom: 16px; }
.pv-group { margin-bottom: 18px; }
.pv-group-header { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f5f7fa; border-radius: 8px; margin-bottom: 8px; }
.pv-group-name { font-size: 13px; font-weight: 600; color: #303133; }
.pv-group-count { font-size: 11px; color: #c0c4cc; background: #fff; padding: 0 6px; border-radius: 8px; min-width: 20px; text-align: center; }
.pv-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border: 1px solid #f0f0f0; border-radius: 6px; margin-bottom: 4px; transition: all 0.15s; }
.pv-row:hover { background: #fafcff; border-color: #dcdfe6; }
.pv-row-left { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.pv-row-name { font-size: 13px; font-weight: 600; color: #303133; }
.pv-row-code { font-size: 11px; color: #c0c4cc; font-family: monospace; }
.pv-row-right { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.pv-footer { display: flex; align-items: center; justify-content: flex-end; gap: 8px; width: 100%; }
.pv-footer-note { flex: 1; font-size: 12px; color: #E6A23C; }
</style>
