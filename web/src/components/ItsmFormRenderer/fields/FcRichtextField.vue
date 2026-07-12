<template>
  <div class="fc-richtext">
    <el-input
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      type="textarea"
      :rows="formCreateInject?.props?.rows || 6"
      :placeholder="formCreateInject?.props?.placeholder || '请输入内容'"
      :disabled="disabled"
    />
  </div>
</template>

<script setup lang="ts">
import { inject } from 'vue'

const props = defineProps<{ modelValue?: any; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: any] }>()

const formCreateInject: any = inject('formCreateInject', null)
</script>

<style scoped>
.fc-richtext { width: 100%; }
</style>
