<template>
  <el-select
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    multiple
    filterable
    remote
    :remote-method="searchUsers"
    :placeholder="formCreateInject?.props?.placeholder || '请选择人员'"
    :disabled="disabled"
    style="width: 100%"
  >
    <el-option
      v-for="u in userOptions"
      :key="u.value"
      :label="u.label"
      :value="u.value"
    />
  </el-select>
</template>

<script setup lang="ts">
import { ref, inject } from 'vue'

const props = defineProps<{ modelValue?: any; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: any] }>()

const formCreateInject: any = inject('formCreateInject', null)

const userOptions = ref<{ label: string; value: any }[]>([])

async function searchUsers(query: string) {
  if (!query) {
    userOptions.value = []
    return
  }
  try {
    // Use the project's existing user search API
    const res = await fetch(`/api/users/search/?q=${encodeURIComponent(query)}`)
      .then(r => r.json())
    userOptions.value = (res?.data || res?.results || []).map((u: any) => ({
      label: u.username || u.name || u.label || '',
      value: u.id ?? u.value,
    }))
  } catch {
    userOptions.value = []
  }
}
</script>
