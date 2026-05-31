<template>
  <div class="render-form">
    <template v-for="(item, idx) in schema" :key="item.tag_code || idx">
      <FormGroup
        v-if="item.type === 'combine' || item.items"
        :config="item"
        :form-data="formData"
        @update="handleUpdate"
      />
      <FormItem
        v-else
        :config="item"
        :value="formData[item.tag_code]"
        @update="(val: any) => handleUpdate(item.tag_code, val)"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import FormItem from './FormItem.vue'
import FormGroup from './FormGroup.vue'

const props = withDefaults(defineProps<{
  schema: any[]
  initialData?: Record<string, any>
}>(), { initialData: () => ({}) })

const emit = defineEmits<{
  change: [data: Record<string, any>]
}>()

const formData = reactive({ ...props.initialData })

watch(() => props.initialData, (val) => {
  Object.assign(formData, val)
}, { deep: true })

function handleUpdate(tagCode: string, value: any) {
  formData[tagCode] = value
  emit('change', { ...formData })
}

defineExpose({
  getValues: () => ({ ...formData }),
  setField: (tagCode: string, value: any) => { formData[tagCode] = value },
})
</script>

<style scoped>
.render-form {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 8px;
  width: 100%;
}
</style>
