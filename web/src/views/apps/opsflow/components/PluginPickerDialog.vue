<template>
  <el-dialog :model-value="props.visible" @update:model-value="emit('update:visible', $event)" title="Select Plugin" width="700px" top="8vh" :close-on-click-modal="false" destroy-on-close>
    <div class="plugin-picker">
      <div class="picker-search">
        <el-input v-model="searchQuery" placeholder="Search plugin name..." clearable prefix-icon="Search" size="small" />
      </div>
      <div class="picker-body">
        <div class="picker-groups">
          <div
            v-for="(items, group) in pluginGroups"
            :key="group"
            class="group-item"
            :class="{ active: activeGroup === group }"
            @click="activeGroup = group"
          >
            <span class="group-name">{{ group }}</span>
            <span class="group-count">{{ items.length }}</span>
          </div>
        </div>
        <div class="picker-plugins">
          <div
            v-for="plugin in filteredPlugins"
            :key="plugin.code"
            class="plugin-card"
            :class="{
              'is-deprecated': isDeprecated(plugin.phase),
              'is-selected': selectedPlugin?.code === plugin.code,
            }"
            @click="selectPlugin(plugin)"
            @dblclick="confirmPlugin(plugin)"
          >
            <div class="plugin-name">
              {{ plugin.name }}
              <el-tag v-if="isDeprecated(plugin.phase)"
                :type="plugin.phase === 2 ? 'danger' : 'warning'"
                size="small" effect="dark" class="deprecated-badge">
                {{ deprecationWarning(plugin.phase, plugin.phase_label) }}
              </el-tag>
            </div>
            <div class="plugin-desc">{{ plugin.description || 'No description' }}</div>
            <div class="plugin-tags">
              <el-tag :type="riskTagType(plugin.risk_level)" size="small" effect="plain">
                {{ plugin.risk_level || 'low' }}
              </el-tag>
            </div>
          </div>
          <el-empty v-if="!filteredPlugins.length" :description="searchQuery ? 'No matching plugins' : 'Select a group'" />
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="emit('update:visible', false)" size="small">Cancel</el-button>
      <el-button type="primary" @click="confirmSelected" size="small" :disabled="!selectedPlugin">Confirm</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { GetPluginGroups } from '/@/api/opsflow/plugins'
import { useOpsflowStore } from '../stores/opsflowStore'

interface PluginItem {
  code: string
  name: string
  risk_level: string
  phase?: number
  phase_label?: string
  versions?: string[]
}

const props = withDefaults(defineProps<{
  visible?: boolean
}>(), { visible: false })
const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'select', plugin: { code: string; name: string; risk_level: string; phase?: number }): void
}>()

const searchQuery = ref('')
const activeGroup = ref('')
const pluginGroups = ref<Record<string, PluginItem[]>>({})
const selectedPlugin = ref<PluginItem | null>(null)

const filteredPlugins = computed(() => {
  const items = pluginGroups.value[activeGroup.value] || []
  if (!searchQuery.value) return items
  const q = searchQuery.value.toLowerCase()
  return items.filter(p => p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q))
})

function isDeprecated(phase?: number): boolean {
  return phase === 1 || phase === 2 // WILL_BE_DEPRECATED or DEPRECATED
}

function deprecationWarning(phase?: number, label?: string): string {
  if (phase === 2) return '已弃用'
  if (phase === 1) return '即将弃用'
  return ''
}

watch(() => props.visible, async (v) => {
  if (v) {
    const store = useOpsflowStore()
    const params: any = {}
    if (store.currentProjectId) {
      params.project_id = store.currentProjectId
    }
    const res = await GetPluginGroups(params)
    pluginGroups.value = res.data || {}
    const keys = Object.keys(pluginGroups.value)
    if (keys.length && !activeGroup.value) activeGroup.value = keys[0]
    selectedPlugin.value = null
    searchQuery.value = ''
  }
})

function selectPlugin(plugin: any) {
  selectedPlugin.value = plugin
}

function confirmPlugin(plugin: any) {
  selectedPlugin.value = plugin
  emit('select', { code: plugin.code, name: plugin.name, risk_level: plugin.risk_level || 'low' })
  emit('update:visible', false)
}

function confirmSelected() {
  if (selectedPlugin.value) {
    emit('select', {
      code: selectedPlugin.value.code,
      name: selectedPlugin.value.name,
      risk_level: selectedPlugin.value.risk_level || 'low',
    })
    emit('update:visible', false)
  }
}

function riskTagType(risk: string): string {
  return { high: 'danger', medium: 'warning', low: 'success' }[risk] || 'info'
}
</script>

<style scoped>
.plugin-picker { display: flex; flex-direction: column; gap: 12px; min-height: 400px; }
.picker-search { flex-shrink: 0; }
.picker-body { display: flex; gap: 16px; flex: 1; min-height: 0; }
.picker-groups {
  width: 160px; flex-shrink: 0; display: flex; flex-direction: column;
  gap: 2px; overflow-y: auto; border-right: 1px solid #f0f0f0; padding-right: 12px;
}
.group-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; cursor: pointer; border-radius: 6px; font-size: 13px;
  transition: all 0.15s;
}
.group-item:hover { background: #f5f7fa; }
.group-item.active { background: #ecf5ff; color: #409EFF; font-weight: 600; }
.group-count {
  font-size: 11px; color: #c0c4cc; background: #f5f7fa;
  padding: 0 6px; border-radius: 8px; min-width: 20px; text-align: center;
}
.picker-plugins {
  flex: 1; display: flex; flex-direction: column; gap: 8px; overflow-y: auto; padding-right: 4px;
}
.plugin-card {
  display: flex; flex-direction: column; gap: 4px;
  padding: 10px 12px; border: 1px solid #ebeef5; border-radius: 6px;
  cursor: pointer; transition: all 0.15s;
}
.plugin-card:hover { border-color: #409EFF; background: #fafcff; }
.plugin-card:active { background: #ecf5ff; }
.plugin-card.is-selected {
  border-color: #337ecc;
  background: linear-gradient(135deg, #ecf5ff, #d9ecff);
  box-shadow: 0 2px 8px rgba(64,158,255,0.15);
}
.plugin-card.is-selected .plugin-name { color: #1a56a0; }
.plugin-card.is-deprecated { opacity: 0.75; border-style: dashed; }
.plugin-card.is-deprecated:hover { border-color: #e6a23c; }
.plugin-name { font-size: 13px; font-weight: 600; color: #303133; display: flex; align-items: center; gap: 6px; }
.deprecated-badge { font-size: 10px; padding: 0 4px; }
.plugin-tags { display: flex; gap: 4px; }
.plugin-desc { font-size: 11px; color: #909399; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
