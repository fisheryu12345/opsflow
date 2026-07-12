<template>
  <el-upload
    :model-value="modelValue"
    :disabled="disabled"
    :action="uploadAction"
    :headers="uploadHeaders"
    :limit="formCreateInject?.props?.limit || 1"
    :accept="formCreateInject?.props?.accept || '*'"
    :on-success="onUploadSuccess"
    :on-remove="onUploadRemove"
    :file-list="fileList"
  >
    <el-button size="small" :disabled="disabled">
      {{ formCreateInject?.props?.btnText || '点击上传' }}
    </el-button>
  </el-upload>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'

const props = defineProps<{ modelValue?: any; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: any] }>()

const formCreateInject: any = inject('formCreateInject', null)

const uploadAction = computed(() =>
  formCreateInject?.props?.action || '/api/upload/')
const uploadHeaders = computed(() => {
  const token = formCreateInject?.api?.getData?.('token') || ''
  return token ? { Authorization: `Bearer ${token}` } : {}
})

const fileList = computed(() => {
  if (!props.modelValue) return []
  if (Array.isArray(props.modelValue)) return props.modelValue
  return typeof props.modelValue === 'string'
    ? props.modelValue.split(',').filter(Boolean).map((url: string, i: number) => ({
        name: `file_${i + 1}`, url,
      }))
    : []
})

function onUploadSuccess(response: any, file: any) {
  file.url = response?.data?.url || response?.url || file.url
  const current = Array.isArray(props.modelValue) ? [...props.modelValue] : []
  current.push(file.url || file.name)
  emit('update:modelValue', current)
}

function onUploadRemove(_file: any, _fileList: any[]) {
  const remaining = _fileList.map((f: any) => f.url || f.name).filter(Boolean)
  emit('update:modelValue', remaining)
}
</script>
