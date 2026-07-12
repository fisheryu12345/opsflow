<template>
  <div class="fc-table">
    <el-table :data="tableData" border size="small" style="width: 100%">
      <el-table-column
        v-for="col in columns"
        :key="col.field"
        :prop="col.field"
        :label="col.title"
        min-width="120"
      >
        <template #default="{ row, $index }">
          <el-input
            v-if="col.type === 'number'"
            v-model="row[col.field]"
            size="small"
            type="number"
            :disabled="disabled"
          />
          <el-input
            v-else
            v-model="row[col.field]"
            size="small"
            :disabled="disabled"
          />
        </template>
      </el-table-column>
      <el-table-column v-if="!disabled" label="操作" width="80" fixed="right">
        <template #default="{ $index }">
          <el-button size="small" text type="danger" @click="removeRow($index)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-button
      v-if="!disabled"
      size="small"
      type="primary"
      text
      style="margin-top: 6px"
      @click="addRow"
    >
      + 添加行
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, inject } from 'vue'

const props = defineProps<{ modelValue?: any; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: any] }>()

const formCreateInject: any = inject('formCreateInject', null)

// Columns defined via props.formCreateRule (same as form-create group pattern)
const columns = computed(() => {
  return formCreateInject?.props?.columns || [
    { field: 'name', title: '名称', type: 'input' },
    { field: 'value', title: '值', type: 'input' },
  ]
})

const tableData = ref<any[]>([])

// Initialize from modelValue
watch(() => props.modelValue, (val) => {
  if (Array.isArray(val)) {
    tableData.value = val.map(row => ({ ...row }))
  } else {
    tableData.value = []
  }
}, { immediate: true })

function syncToModel() {
  emit('update:modelValue', JSON.parse(JSON.stringify(tableData.value)))
}

function addRow() {
  const newRow: Record<string, any> = {}
  columns.value.forEach(col => { newRow[col.field] = '' })
  tableData.value.push(newRow)
  syncToModel()
}

function removeRow(index: number) {
  tableData.value.splice(index, 1)
  syncToModel()
}

// Watch table changes
watch(tableData, () => syncToModel(), { deep: true })
</script>

<style scoped>
.fc-table {
  width: 100%;
}
</style>
