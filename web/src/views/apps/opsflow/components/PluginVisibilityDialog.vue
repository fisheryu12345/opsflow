<template>
  <el-dialog :model-value="visible" @update:model-value="emit('update:visible', $event)"
    title="Plugin Visibility by Project" width="820px" top="5vh" destroy-on-close
    class="opsflow-dialog pv-dialog">
    <div v-loading="loading" class="pv-body">
      <!-- Stats bar -->
      <div class="pv-stats">
        <div class="pv-stat"><b>{{ totalPlugins }}</b> plugins</div>
        <el-tag type="warning" size="small" effect="plain">{{ restrictedCount }} restricted</el-tag>
        <el-tag type="success" size="small" effect="plain">{{ unrestrictedCount }} all projects</el-tag>
      </div>

      <!-- Search -->
      <el-input v-model="searchQuery" placeholder="Search plugin name or code..."
        clearable prefix-icon="Search" size="small" class="pv-search" />

      <!-- Plugin list grouped -->
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
              :model-value="plugin.restricted"
              size="small"
              active-text="Restricted"
              inactive-text="All projects"
              @change="(val: boolean) => onToggleRestrict(plugin, val)"
            />
            <template v-if="plugin.restricted">
              <el-select
                :model-value="plugin.projectIds"
                @update:model-value="(val: number[]) => onProjectChange(plugin, val)"
                multiple filterable collapse-tags collapse-tags-tooltip
                placeholder="Select projects..." size="small" style="width:260px">
                <el-option v-for="proj in allProjects" :key="proj.id"
                  :label="proj.name" :value="proj.id" />
              </el-select>
            </template>
            <span v-else class="pv-all-label">Visible to all</span>
          </div>
        </div>
      </div>

      <el-empty v-if="filteredPlugins.length === 0 && !loading"
        description="No plugins found" :image-size="60" />
    </div>

    <template #footer>
      <div class="pv-footer">
        <span class="pv-footer-note">{{ changedCount > 0 ? `${changedCount} unsaved change(s)` : '' }}</span>
        <el-button size="small" @click="handleReset">Reset</el-button>
        <el-button size="small" type="primary" :loading="saving" @click="handleSave"
          :disabled="changedCount === 0">Save Changes</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { GetPluginsVisibilityList, BatchSetPluginsVisibility } from '/@/api/opsflow/plugins'
import { GetProjects } from '/@/api/opsflow/projects'

interface PluginVisibilityItem {
  code: string
  name: string
  group: string
  description: string
  risk_level: string
  allowed_projects: number[]
  restricted: boolean
}

interface ProjectItem {
  id: number
  name: string
}

const props = withDefaults(defineProps<{ visible?: boolean }>(), { visible: false })
const emit = defineEmits<{ (e: 'update:visible', val: boolean): void }>()

const loading = ref(false)
const saving = ref(false)
const searchQuery = ref('')
const allProjects = ref<ProjectItem[]>([])
const plugins = ref<PluginVisibilityItem[]>([])
const originalPlugins = ref<string>('') // JSON serialized for diff detection

const filteredPlugins = computed(() => {
  if (!searchQuery.value) return plugins.value
  const q = searchQuery.value.toLowerCase()
  return plugins.value.filter(p =>
    p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q)
  )
})

const groupedPlugins = computed(() => {
  const map: Record<string, PluginVisibilityItem[]> = {}
  for (const p of filteredPlugins.value) {
    (map[p.group] ||= []).push(p)
  }
  return map
})

const totalPlugins = computed(() => plugins.value.length)
const restrictedCount = computed(() => plugins.value.filter(p => p.restricted).length)
const unrestrictedCount = computed(() => totalPlugins.value - restrictedCount.value)
const changedCount = computed(() => {
  const current = JSON.stringify(plugins.value.map(p => ({
    code: p.code, projectIds: [...p.allowed_projects].sort()
  })))
  return current !== originalPlugins.value
    ? plugins.value.filter((p, i) => {
        const orig = JSON.parse(originalPlugins.value || '[]')
        const o = orig[i] || {}
        return JSON.stringify([...p.allowed_projects].sort()) !== JSON.stringify((o.projectIds || []).sort())
      }).length
    : 0
})

function onToggleRestrict(plugin: PluginVisibilityItem, restricted: boolean) {
  plugin.restricted = restricted
  if (!restricted) {
    plugin.allowed_projects = []
  } else if (plugin.allowed_projects.length === 0) {
    // When switching to restricted with no projects selected, default to first project
    if (allProjects.value.length > 0) {
      plugin.allowed_projects = [allProjects.value[0].id]
    }
  }
}

function onProjectChange(plugin: PluginVisibilityItem, ids: number[]) {
  plugin.allowed_projects = ids
  plugin.restricted = ids.length > 0
}

async function loadData() {
  loading.value = true
  try {
    const [pluginRes, projectRes] = await Promise.all([
      GetPluginsVisibilityList(),
      GetProjects(),
    ])
    allProjects.value = ((projectRes as any).data || []).filter((p: any) => p.is_active !== false)
    plugins.value = (pluginRes.data?.data || pluginRes.data || []).map((p: any) => ({
      code: p.code,
      name: p.name,
      group: p.group || 'General',
      description: p.description || '',
      risk_level: p.risk_level || 'low',
      allowed_projects: p.allowed_projects || [],
      restricted: (p.allowed_projects || []).length > 0,
    }))
    originalPlugins.value = JSON.stringify(plugins.value.map(p => ({
      code: p.code, projectIds: [...p.allowed_projects].sort()
    })))
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Failed to load plugin visibility data')
    plugins.value = []
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const updates = plugins.value
      .filter(p => p.restricted)
      .map(p => ({ code: p.code, project_ids: p.allowed_projects }))
    await BatchSetPluginsVisibility(updates)
    // Also clear restrictions for plugins that are no longer restricted
    const clearUpdates = plugins.value
      .filter(p => !p.restricted && p.allowed_projects.length > 0)
      .map(p => ({ code: p.code, project_ids: [] }))
    if (clearUpdates.length > 0) {
      await BatchSetPluginsVisibility(clearUpdates)
    }
    ElMessage.success('Plugin visibility updated')
    originalPlugins.value = JSON.stringify(plugins.value.map(p => ({
      code: p.code, projectIds: [...p.allowed_projects].sort()
    })))
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Save failed')
  } finally {
    saving.value = false
  }
}

function handleReset() {
  loadData()
  ElMessage.info('Changes discarded')
}

watch(() => props.visible, (v) => {
  if (v) {
    loadData()
    searchQuery.value = ''
  }
})
</script>

<style scoped>
.pv-dialog :deep(.el-dialog__body) { padding: 0; }
.pv-body { max-height: 65vh; overflow-y: auto; padding: 18px 20px; }
.pv-stats { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; font-size: 13px; color: #606266; }
.pv-stats b { color: #303133; font-size: 15px; }
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
.pv-all-label { font-size: 12px; color: #67C23A; font-weight: 500; }
.pv-footer { display: flex; align-items: center; justify-content: flex-end; gap: 8px; width: 100%; }
.pv-footer-note { flex: 1; font-size: 12px; color: #E6A23C; }
</style>
