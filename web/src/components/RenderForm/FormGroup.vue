<template>
  <div class="form-group" :style="{ gridColumn: 'span 12' }">
    <div v-if="config.name" class="group-title">{{ config.name }}</div>
    <div class="group-body">
      <template v-for="(child, idx) in config.items" :key="child.tag_code || idx">
        <FormGroup
          v-if="child.type === 'combine' || child.items"
          :config="child"
          :form-data="formData"
          @update="(tagCode: string, val: any) => emit('update', tagCode, val)"
        />
        <FormItem
          v-else
          :config="child"
          :value="formData?.[child.tag_code]"
          @update="(val: any) => emit('update', child.tag_code, val)"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import FormItem from './FormItem.vue'

defineProps<{
  config: any
  formData?: Record<string, any>
}>()

const emit = defineEmits<{
  update: [tagCode: string, value: any]
}>()
</script>

<style scoped>
.form-group { width: 100%; }
.group-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 6px;
  margin-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}
.group-body {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 8px;
}
</style>
