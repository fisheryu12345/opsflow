<template>
  <div class="datatable-editor">
    <el-table :data="rows" border size="small" style="width:100%" max-height="300">
      <el-table-column v-for="col in columns" :key="col.key" :label="col.label" :width="col.width" :min-width="col.minWidth || 120">
        <template #default="{ row, $index }">
          <el-input v-if="col.type === 'input'" v-model="row[col.key]" size="small" :placeholder="col.placeholder || ''" />
          <el-select v-else-if="col.type === 'select'" v-model="row[col.key]" size="small" style="width:100%"
            :placeholder="col.placeholder || ''" filterable>
            <el-option v-for="opt in (col.options || [])" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <span v-else>{{ row[col.key] }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" fixed="right">
        <template #default="{ $index }">
          <el-button size="small" type="danger" link @click="removeRow($index)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="datatable-actions">
      <el-button size="small" type="primary" text @click="addRow">
        <el-icon><Plus /></el-icon> 添加行
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Delete } from '@element-plus/icons-vue'

interface ColumnDef {
  key: string
  label: string
  type?: 'input' | 'select'
  width?: number
  minWidth?: number
  placeholder?: string
  options?: { label: string; value: any }[]
}

const props = withDefaults(defineProps<{
  modelValue?: any
  attrs?: { columns?: ColumnDef[] }
  disabled?: boolean
}>(), { modelValue: () => [] })

const emit = defineEmits(['update:modelValue'])

const columns = computed<ColumnDef[]>(() => props.attrs?.columns || [{ key: 'value', label: '值' }])

const rows = computed({
  get: () => {
    const v = props.modelValue
    if (Array.isArray(v)) return v
    return []
  },
  set: (v) => emit('update:modelValue', v),
})

function addRow() {
  const newRow: Record<string, any> = {}
  columns.value.forEach((col) => { newRow[col.key] = '' })
  rows.value = [...rows.value, newRow]
}

function removeRow(index: number) {
  const next = rows.value.filter((_: any, i: number) => i !== index)
  rows.value = next
}
</script>

<style scoped>
.datatable-editor { display: flex; flex-direction: column; gap: 6px; }
.datatable-actions { display: flex; }
</style>
