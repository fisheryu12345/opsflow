<template>
  <el-dialog v-model="visible" :title="$t('message.agentPage.fileTitle')" width="500px" class="opsflow-dialog" @closed="onClosed">
    <el-form :label-width="100">
      <el-form-item :label="$t('message.agentPage.fileTarget')">
        <el-tag>{{ target?.hostname }} ({{ target?.ip }})</el-tag>
      </el-form-item>
      <el-form-item :label="$t('message.agentPage.fileSource')">
        <div style="display:flex;gap:8px">
          <el-input v-model="source" :placeholder="$t('message.agentPage.fileSourcePlaceholder')" style="flex:1" />
          <el-button :icon="FolderOpened" @click="triggerPick">{{ $t('message.agentPage.browse') }}</el-button>
        </div>
        <input ref="fileInputRef" type="file" style="display:none" @change="onFilePicked" />
      </el-form-item>
      <el-form-item :label="$t('message.agentPage.fileDest')">
        <el-input v-model="dest" :placeholder="$t('message.agentPage.fileDestPlaceholder')" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ $t('message.agentPage.cancel') }}</el-button>
      <el-button type="primary" @click="doPush">{{ $t('message.agentPage.push') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { FolderOpened } from '@element-plus/icons-vue'
import * as agentApi from '/@/api/agent'
import type { AgentInstance } from '/@/api/agent'

const { t } = useI18n()

const props = defineProps<{
  modelValue: boolean
  target: AgentInstance | null
}>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const source = ref('')
const dest = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)

watch(() => props.modelValue, (v) => {
  if (v) { source.value = ''; dest.value = ''; selectedFile.value = null }
})

function triggerPick() { fileInputRef.value?.click() }
function onFilePicked(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) { selectedFile.value = input.files[0]; source.value = input.files[0].name }
}
function doPush() {
  const formData = new FormData()
  formData.append('target_host', props.target?.ip || '')
  formData.append('target_path', dest.value)
  if (selectedFile.value) formData.append('file', selectedFile.value)
  else formData.append('source_path', source.value)
  agentApi.pushFile(formData).then(() => {
    ElMessage.success(t('message.agentPage.msgFileSuccess'))
    visible.value = false
  }).catch(() => { selectedFile.value = null })
}
</script>
