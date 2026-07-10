<template>
  <div class="des-toolbar" :class="{ collapsed: collapsed }">
    <div class="des-toolbar-left">
      <el-button text size="small" @click="$emit('back')">
        <el-icon><ArrowLeft /></el-icon> {{ $t('message.common.back') }}
      </el-button>
      <el-tag v-if="workflow" :type="workflow.is_draft ? 'warning' : 'success'" size="small" style="margin-left:8px;">
        {{ workflow.is_draft ? '草稿' : '已发布' }}
      </el-tag>
    </div>
    <div class="des-toolbar-center">
      <el-input v-if="workflow" v-model="workflow.name" size="small" style="width:300px;font-weight:600;"
        placeholder="流程名称" @input="onNameChange" />
    </div>
    <div class="des-toolbar-right">
      <el-tooltip content="放大" :show-after="500">
        <el-button size="small" :icon="ZoomIn" @click="$emit('zoomIn')" circle />
      </el-tooltip>
      <span class="zoom-level">{{ zoomLevel }}%</span>
      <el-tooltip content="缩小" :show-after="500">
        <el-button size="small" :icon="ZoomOut" @click="$emit('zoomOut')" circle />
      </el-tooltip>
      <el-tooltip content="适应画布" :show-after="500">
        <el-button size="small" :icon="FullScreen" @click="$emit('fitCanvas')" circle />
      </el-tooltip>
      <el-tooltip content="自动布局" :show-after="500">
        <el-button size="small" :icon="Operation" @click="$emit('autoLayout')" circle />
      </el-tooltip>

      <div class="toolbar-divider" />

      <el-tooltip content="AI 生成" :show-after="500">
        <el-button size="small" :icon="MagicStick" @click="$emit('aiGenerate')" circle />
      </el-tooltip>
<el-tooltip content="保存" :show-after="500">
        <el-button size="small" :icon="Upload" :loading="saving" @click="$emit('save')" circle class="btn-save" />
      </el-tooltip>
      <el-tooltip content="部署" :show-after="500">
        <el-button size="small" type="success" :icon="Upload" @click="$emit('deploy')" :disabled="workflow?.is_draft === false">
          部署
        </el-button>
      </el-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, ZoomIn, ZoomOut, FullScreen, Operation, MagicStick, Upload } from '@element-plus/icons-vue'

defineProps<{
  workflow?: any
  saving?: boolean
  collapsed?: boolean
  zoomLevel?: number
}>()

const emit = defineEmits<{
  back: []
  zoomIn: []
  zoomOut: []
  fitCanvas: []
  autoLayout: []
  aiGenerate: []
  save: []
  deploy: []
  nameChange: [name: string]
}>()

function onNameChange(val: string) {
  emit('nameChange', val)
}
</script>

<style scoped>
.des-toolbar {
  display: flex; align-items: center; gap: 8px; padding: 6px 16px;
  background: rgba(255,255,255,0.95);
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}
.des-toolbar-left { display: flex; align-items: center; gap: 4px; }
.des-toolbar-center { flex: 1; display: flex; justify-content: center; }
.des-toolbar-right { display: flex; align-items: center; gap: 4px; }
.zoom-level { font-size: 11px; color: #909399; min-width: 32px; text-align: center; font-family: monospace; }
.toolbar-divider { width: 1px; height: 20px; background: #e4e7ed; margin: 0 4px; }
.btn-save { color: #667eea; }
</style>
