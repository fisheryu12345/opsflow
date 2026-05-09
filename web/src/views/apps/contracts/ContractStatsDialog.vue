<template>
  <el-dialog v-model="visible" title="合约统计信息" width="600px" :close-on-click-modal="false">
    <div v-if="stats">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="合约总数">
          <el-tag type="primary" size="large">{{ stats.total }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">按交易所统计</el-divider>
      <el-table :data="stats.by_exchange" border stripe max-height="200">
        <el-table-column prop="label" label="交易所" width="120" />
        <el-table-column prop="count" label="数量" align="right" />
      </el-table>
    </div>
    <div v-else style="text-align: center; padding: 40px;">
      <el-empty description="暂无数据" />
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ContractStats } from '/@/types/trading'

const props = withDefaults(defineProps<{
  modelValue: boolean
  stats?: ContractStats | null
}>(), {})

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
}>()

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => { emit('update:modelValue', v) })
</script>
