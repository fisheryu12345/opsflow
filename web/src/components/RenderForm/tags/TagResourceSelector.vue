<template>
  <div class="resource-selector">
    <!-- 搜索框 -->
    <el-input
      v-model="searchQuery"
      :placeholder="'搜索资源...'"
      size="small"
      clearable
      style="width:100%; margin-bottom: 6px;"
      @input="onSearchDebounced"
    />

    <!-- 已选项 -->
    <div class="selected-tags" v-if="selected.length">
      <el-tag v-for="item in selected" :key="item.value || item" closable size="small"
        @close="removeItem(item.value || item)" type="info">
        {{ item.label || item }}
      </el-tag>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="resource-loading">
      <el-icon class="is-loading"><Loading /></el-icon> 加载中...
    </div>

    <!-- 集群分组模式 -->
    <template v-else-if="groupBy && groupedData.length">
      <el-collapse v-model="openGroups" size="small">
        <el-collapse-item v-for="group in groupedData" :key="group.label" :name="group.label" :title="`${group.label} (${group.children.length})`">
          <div class="group-items">
            <div v-for="item in group.children" :key="item.value"
              :class="['resource-item', { selected: isSelected(item) }]"
              @click="toggleItem(item)">
              <el-checkbox :checked="isSelected(item)" size="small" @click.stop />
              <div class="resource-info">
                <span class="resource-name">{{ item.label }}</span>
                <span class="resource-meta" v-if="item.ip || item.model">
                  {{ item.ip ? item.ip : '' }}{{ item.ip && item.model ? ' · ' : '' }}{{ item.model ? item.model : '' }}
                </span>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </template>

    <!-- 列表模式 -->
    <div v-else-if="!loading && flatData.length" class="resource-list">
      <div v-for="item in flatData" :key="item.value"
        :class="['resource-item', { selected: isSelected(item) }]"
        @click="toggleItem(item)">
        <el-checkbox v-if="multiple" :checked="isSelected(item)" size="small" @click.stop />
        <el-radio v-else :checked="isSelected(item)" size="small" @click.stop />
        <div class="resource-info">
          <span class="resource-name">{{ item.label }}</span>
          <span class="resource-meta" v-if="item.ip || item.model || item.cluster">
            {{ [item.ip, item.model, item.cluster].filter(Boolean).join(' · ') }}
          </span>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && flatData.length === 0 && groupedData.length === 0" description="无匹配资源" :image-size="40" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'

interface ResourceItem {
  value: string
  label: string
  ip?: string
  model?: string
  cluster?: string
  rack?: string
}

interface GroupData {
  label: string
  value: string
  children: ResourceItem[]
}

const props = withDefaults(defineProps<{
  modelValue?: any
  disabled?: boolean
  attrs?: {
    api_endpoint?: string
    group_by?: string
    multiple?: boolean
    value_key?: string
    label_key?: string
  }
}>(), {
  modelValue: () => [],
  attrs: () => ({}),
})

const emit = defineEmits(['update:modelValue'])

const apiEndpoint = computed(() => props.attrs?.api_endpoint || '')
const groupBy = computed(() => props.attrs?.group_by || '')
const multiple = computed(() => props.attrs?.multiple !== false)
const valueKey = computed(() => props.attrs?.value_key || 'value')
const labelKey = computed(() => props.attrs?.label_key || 'label')

const searchQuery = ref('')
const loading = ref(false)
const flatData = ref<ResourceItem[]>([])
const groupedData = ref<GroupData[]>([])
const openGroups = ref<string[]>([])

const selected = computed(() => {
  const v = props.modelValue
  if (Array.isArray(v)) return v
  return []
})

function isSelected(item: ResourceItem): boolean {
  const val = item[valueKey.value as keyof ResourceItem] || item.value
  return selected.value.some((s: any) => (typeof s === 'string' ? s : s.value || s) === val)
}

function toggleItem(item: ResourceItem) {
  const val = item[valueKey.value as keyof ResourceItem] || item.value
  const label = item[labelKey.value as keyof ResourceItem] || item.label
  const entry = { value: val, label }
  const current = [...selected.value]
  const idx = current.findIndex((s: any) => {
    const sv = typeof s === 'string' ? s : s.value || s
    return sv === val
  })
  if (idx >= 0) {
    current.splice(idx, 1)
  } else if (multiple.value) {
    current.push(entry)
  } else {
    emit('update:modelValue', [entry])
    return
  }
  emit('update:modelValue', current)
}

function removeItem(val: string) {
  const current = selected.value.filter((s: any) => {
    const sv = typeof s === 'string' ? s : s.value || s
    return sv !== val
  })
  emit('update:modelValue', current)
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchDebounced() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(loadData, 300)
}

async function loadData() {
  if (!apiEndpoint.value) return
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchQuery.value) params.set('q', searchQuery.value)
    if (groupBy.value) params.set('group_by', groupBy.value)
    const qs = params.toString()
    const url = apiEndpoint.value + (qs ? `?${qs}` : '')
    const res = await fetch(url)
    const json = await res.json()
    const data = json.data || []

    if (groupBy.value && data.length && data[0]?.children) {
      groupedData.value = data
      flatData.value = []
      openGroups.value = data.map((g: GroupData) => g.label)
    } else {
      flatData.value = data
      groupedData.value = []
    }
  } catch {
    flatData.value = []
    groupedData.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.resource-selector { display: flex; flex-direction: column; gap: 4px; }
.selected-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.resource-loading { display: flex; align-items: center; gap: 6px; color: #909399; font-size: 13px; padding: 12px 0; justify-content: center; }
.resource-list { display: flex; flex-direction: column; gap: 2px; max-height: 280px; overflow-y: auto; }
.resource-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px;
  border-radius: 4px; cursor: pointer; transition: background 0.15s;
}
.resource-item:hover { background: #f0f5ff; }
.resource-item.selected { background: #e6f0ff; }
.resource-info { display: flex; flex-direction: column; min-width: 0; }
.resource-name { font-size: 13px; color: #333; font-weight: 500; }
.resource-meta { font-size: 11px; color: #909399; }
.group-items { display: flex; flex-direction: column; gap: 2px; }
</style>
