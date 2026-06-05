<template>
  <div class="editor-stub">
    <el-input
      type="textarea"
      :model-value="modelValue"
      @input="$emit('update:modelValue', $event)"
      :rows="6"
      placeholder="富文本编辑器 (简化版)"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
