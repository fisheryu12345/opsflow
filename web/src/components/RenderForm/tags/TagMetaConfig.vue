<template>
  <div class="meta-config">
    <div class="meta-items" v-if="items.length">
      <div v-for="(item, i) in items" :key="i" class="meta-item-row">
        <el-input v-model="item.label" placeholder="Label" size="small" style="width:120px" />
        <el-input v-model="item.value" placeholder="Value" size="small" style="width:120px" />
        <el-button size="small" type="danger" link @click="removeItem(i)">
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
    </div>
    <div class="meta-actions">
      <el-button size="small" type="primary" text @click="addItem">
        <el-icon><Plus /></el-icon> Add option
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Plus, Delete } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  modelValue?: any
  disabled?: boolean
}>(), { modelValue: () => [] })
const emit = defineEmits(['update:modelValue'])

const items = computed({
  get: () => {
    const v = props.modelValue
    if (Array.isArray(v)) return v
    return []
  },
  set: (v) => emit('update:modelValue', v),
})

function addItem() {
  items.value = [...items.value, { label: '', value: '' }]
}
function removeItem(index: number) {
  items.value = items.value.filter((_: any, i: number) => i !== index)
}
</script>

<style scoped>
.meta-config { display: flex; flex-direction: column; gap: 4px; }
.meta-item-row { display: flex; gap: 4px; align-items: center; }
.meta-actions { display: flex; }
</style>
