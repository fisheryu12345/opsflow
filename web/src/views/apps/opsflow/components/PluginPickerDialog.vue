<template>
  <el-dialog :model-value="props.visible" @update:model-value="emit('update:visible', $event)" title="选择插件" width="700px" top="8vh" :close-on-click-modal="false" destroy-on-close>
    <div class="plugin-picker">
      <div class="picker-search">
        <el-input v-model="searchQuery" placeholder="搜索插件名称..." clearable prefix-icon="Search" size="small" />
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
            @click="selectPlugin(plugin)"
            @dblclick="confirmPlugin(plugin)"
          >
            <div class="plugin-name">{{ plugin.name }}</div>
            <div class="plugin-desc">{{ plugin.description || '暂无描述' }}</div>
            <el-tag :type="riskTagType(plugin.risk_level)" size="small" effect="plain">
              {{ plugin.risk_level || 'low' }}
            </el-tag>
          </div>
          <el-empty v-if="!filteredPlugins.length" :description="searchQuery ? '无匹配插件' : '请选择分组'" />
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="emit('update:visible', false)" size="small">取消</el-button>
      <el-button type="primary" @click="confirmSelected" size="small" :disabled="!selectedPlugin">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { GetPluginGroups } from '/@/api/opsflow/plugins'

const props = withDefaults(defineProps<{
  visible?: boolean
}>(), { visible: false })
const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'select', plugin: { code: string; name: string; risk_level: string }): void
}>()

const searchQuery = ref('')
const activeGroup = ref('')
const pluginGroups = ref<Record<string, { code: string; name: string; risk_level: string }[]>>({})
const selectedPlugin = ref<{ code: string; name: string; risk_level: string } | null>(null)

const filteredPlugins = computed(() => {
  const items = pluginGroups.value[activeGroup.value] || []
  if (!searchQuery.value) return items
  const q = searchQuery.value.toLowerCase()
  return items.filter(p => p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q))
})

watch(() => props.visible, async (v) => {
  if (v) {
    const res = await GetPluginGroups()
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
  visible.value = false
}

function confirmSelected() {
  if (selectedPlugin.value) {
    emit('select', {
      code: selectedPlugin.value.code,
      name: selectedPlugin.value.name,
      risk_level: selectedPlugin.value.risk_level || 'low',
    })
    visible.value = false
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
.plugin-name { font-size: 13px; font-weight: 600; color: #303133; }
.plugin-desc { font-size: 11px; color: #909399; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
