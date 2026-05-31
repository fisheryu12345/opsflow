<template>
  <div class="scheme-selector">
    <el-select v-model="selectedSchemeId" placeholder="Select execution scheme (optional)" clearable filterable size="small" style="width: 100%">
      <el-option v-for="s in schemes" :key="s.id" :label="s.name + (s.is_default ? ' (Default)' : '')" :value="s.id">
        <span>{{ s.name }}</span>
        <span v-if="s.description" class="scheme-desc"> — {{ s.description }}</span>
        <el-tag v-if="s.is_default" size="small" type="success" style="margin-left: 6px">Default</el-tag>
      </el-option>
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { GetSchemes } from '/@/api/opsflow/templates'

const props = defineProps<{ templateId: number | null }>()
const emit = defineEmits<{ select: [schemeId: number | null] }>()

const schemes = ref<any[]>([])
const selectedSchemeId = ref<number | null>(null)

watch(() => props.templateId, async (id) => {
  selectedSchemeId.value = null
  if (!id) { schemes.value = []; return }
  try {
    const res = await GetSchemes(id)
    schemes.value = res.data?.data || res.data || []
    // Auto-select default scheme
    const def = schemes.value.find((s: any) => s.is_default)
    if (def) selectedSchemeId.value = def.id
  } catch { schemes.value = [] }
}, { immediate: true })

watch(selectedSchemeId, (val) => emit('select', val))
</script>

<style scoped>
.scheme-selector { width: 100%; }
.scheme-desc { color: #909399; font-size: 12px; }
</style>
