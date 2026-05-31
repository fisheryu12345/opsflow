<template>
  <div class="var-mapping">
    <div v-if="!rows.length" class="mapping-empty">No variable mappings configured</div>
    <div v-for="(row, i) in rows" :key="i" class="mapping-row">
      <el-input v-model="row.parent_key" placeholder="Parent var (e.g. ${ip})" size="small" style="width:45%" />
      <el-icon style="color:#C0C4CC"><ArrowRight /></el-icon>
      <el-input v-model="row.child_key" placeholder="Child template key" size="small" style="width:45%" />
      <el-button size="small" type="danger" link @click="removeRow(i)">
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
    <div class="mapping-actions">
      <el-button size="small" type="primary" text @click="addRow">
        <el-icon><Plus /></el-icon> Add mapping
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Plus, Delete, ArrowRight } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  disabled?: boolean
}>(), { modelValue: () => [] })
const emit = defineEmits(['update:modelValue'])

const rows = computed({
  get: () => {
    const v = props.modelValue
    if (Array.isArray(v)) return v
    return []
  },
  set: (v) => emit('update:modelValue', v),
})

function addRow() {
  rows.value = [...rows.value, { parent_key: '', child_key: '' }]
}
function removeRow(index: number) {
  rows.value = rows.value.filter((_: any, i: number) => i !== index)
}
</script>

<style scoped>
.var-mapping { display: flex; flex-direction: column; gap: 6px; }
.mapping-empty { font-size: 12px; color: #C0C4CC; padding: 8px 0; text-align: center; }
.mapping-row { display: flex; gap: 6px; align-items: center; }
.mapping-actions { display: flex; }
</style>
