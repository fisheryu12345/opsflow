<template>
  <div class="fc-itsm-body" :class="{ 'fc-itsm-fullscreen': isFullscreen }" :style="{ height: bodyHeight }">
    <!-- Settings gear button (left sidebar area) -->
    <el-tooltip content="设计器设置" placement="right">
      <el-button class="fc-itsm-settings-btn" :icon="Setting" circle size="small" @click="showSettings = true" />
    </el-tooltip>

    <fc-designer
      v-if="presetsReady"
      ref="designerRef"
      :config="designerConfig"
      :locale="designerLocale"
      height="100%"
    >
      <template #handle>
        <el-tooltip :content="isFullscreen ? '退出全屏' : '全屏'" placement="bottom">
          <el-button :icon="FullScreen" text size="small" @click="toggleFullscreen" />
        </el-tooltip>
        <el-divider direction="vertical" />
        <el-button size="small" @click="emit('cancel')">{{ $t('message.common.cancel') }}</el-button>
        <el-button size="small" type="primary" @click="handleConfirm">
          {{ $t('message.formDesigner.save') }}
        </el-button>
      </template>
    </fc-designer>
    <div v-else class="fc-itsm-loading">
      <el-icon class="is-loading"><Loading /></el-icon> 加载预设数据...
    </div>

    <!-- Settings panel -->
    <FcDesignerSettingsPanel :visible="showSettings" @close="showSettings = false" />

    <!-- Resize handle -->
    <div class="fc-itsm-resize-handle" @mousedown="startResize" v-if="!isFullscreen" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading, Setting, FullScreen } from '@element-plus/icons-vue'
import zhCN from '@form-create/designer/locale/zh-cn'
import en from '@form-create/designer/locale/en'
import { presetApi } from '/@/api/itsm/index'
import {
  designerConfig,
  initDesignerSettings,
  saveDesignerSettings,
  registerCustomComponents,
  presetOptionList,
  presetDataMap,
  setDesignerInstance,
} from './fcExtensions'
import FcDesignerSettingsPanel from './FcDesignerSettingsPanel.vue'

const { locale } = useI18n()

const designerLocale = computed(() => {
  return locale.value === 'en' ? en : zhCN
})

const props = defineProps<{ fields?: any[] }>()
const emit = defineEmits<{ save: [fields: any[]]; cancel: [] }>()

const designerRef = ref()
const presetsReady = ref(false)
const showSettings = ref(false)

// ── Fullscreen ──
const isFullscreen = ref(true)
function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
}

// ── Resize ──
const bodyHeight = ref('100vh')
let resizeStartY = 0
let resizeStartHeight = 0

function startResize(e: MouseEvent) {
  resizeStartY = e.clientY
  resizeStartHeight = (e.target as HTMLElement).parentElement!.offsetHeight
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'ns-resize'
  document.body.style.userSelect = 'none'
}

function onResize(e: MouseEvent) {
  const delta = e.clientY - resizeStartY
  const newHeight = Math.max(300, resizeStartHeight + delta)
  bodyHeight.value = newHeight + 'px'
}

function stopResize() {
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

onUnmounted(() => {
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
})

// Load presets BEFORE rendering fc-designer so baseRule.options is populated
onMounted(async () => {
  // First, restore designer settings from localStorage / DB
  await initDesignerSettings()

  try {
    const res = await presetApi.list({ preset_type: 'options', page_size: 200 })
    const list = (res as any).data || (res as any).results || []
    presetOptionList.value = list.map((p: any) => ({ label: p.name, value: p.id }))
    presetDataMap.clear()
    for (const p of list) {
      if (p.value) {
        // Store with both string and number keys (fc-designer may return either)
        presetDataMap.set(p.id, p.value)
        presetDataMap.set(String(p.id), p.value)
      }
    }
  } catch {
    presetOptionList.value = []
  }
  presetsReady.value = true
})

// Expand preset ID → actual options in rule.options
function expandPresets(rules: any[]) {
  if (!presetDataMap.size) return
  for (const r of rules) {
    if (r.itsmPresetId != null) {
      const options = presetDataMap.get(r.itsmPresetId)
      if (options) {
        r.options = JSON.parse(JSON.stringify(options))
      }
    }
  }
}

// Register custom components + inject preset selector into base config panel
watch(designerRef, (instance) => {
  if (instance) {
    registerCustomComponents(instance)
    // Store designer instance for preset change handler (used by componentRule)
    setDesignerInstance(instance)

    if (props.fields?.length) {
      expandPresets(props.fields)
      instance.setRule(props.fields)
    }
  }
}, { immediate: true })

// Watch for external field changes (re-open dialog with new fields)
watch(() => props.fields, (f) => {
  if (f && designerRef.value) {
    expandPresets(f)
    designerRef.value.setRule(f)
  }
})

function handleConfirm() {
  if (!designerRef.value) return
  const rules = designerRef.value.getRule()
  expandPresets(rules)
  emit('save', rules)
}
</script>

<style scoped>
.fc-itsm-body {
  position: relative;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}
.fc-itsm-body.fc-itsm-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 3000;
  border-radius: 0;
  border: none;
  background: #fff;
}
.fc-itsm-settings-btn {
  position: absolute;
  bottom: 12px;
  left: 6px;
  z-index: 100;
  opacity: 0.5;
  transition: opacity 0.2s;
}
.fc-itsm-settings-btn:hover {
  opacity: 1;
}
.fc-itsm-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  color: #909399;
  font-size: 14px;
}
.fc-itsm-resize-handle {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 6px;
  cursor: ns-resize;
  z-index: 200;
}
.fc-itsm-resize-handle:hover {
  background: #409EFF;
  opacity: 0.3;
}
</style>
