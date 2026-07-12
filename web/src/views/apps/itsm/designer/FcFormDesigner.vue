<template>
  <div class="fc-itsm-body">
    <fc-designer
      v-if="presetsReady"
      ref="designerRef"
      :config="designerConfig"
      :locale="designerLocale"
      height="560px"
    />
    <div v-else class="fc-itsm-loading">
      <el-icon class="is-loading"><Loading /></el-icon> 加载预设数据...
    </div>
  </div>
  <div class="fc-itsm-footer">
    <el-button @click="emit('cancel')">{{ $t('message.common.cancel') }}</el-button>
    <el-button type="primary" @click="handleConfirm">
      {{ $t('message.formDesigner.save') }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loading } from '@element-plus/icons-vue'
import zhCN from '@form-create/designer/locale/zh-cn'
import en from '@form-create/designer/locale/en'
import { presetApi } from '/@/api/itsm/index'
import {
  designerConfig,
  registerCustomComponents,
  presetOptionList,
  presetDataMap,
} from './fcExtensions'

const { locale } = useI18n()

const designerLocale = computed(() => {
  return locale.value === 'en' ? en : zhCN
})

const props = defineProps<{ fields?: any[] }>()
const emit = defineEmits<{ save: [fields: any[]]; cancel: [] }>()

const designerRef = ref()
const presetsReady = ref(false)

// Load presets BEFORE rendering fc-designer so baseRule.options is populated
onMounted(async () => {
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
    // Capture designer instance for preset change handler
    const designer = instance
    instance.setBaseRuleConfig(() => [{
      type: 'select',
      field: 'itsmPresetId',
      title: '选项预设',
      props: { clearable: true, placeholder: '选择预设加载选项' },
      options: presetOptionList.value,
      on: {
        change: (presetId: any) => {
          if (presetId == null || presetId === '') {
            const rules = designer.getRule()
            for (const r of rules) { if (r.itsmPresetId == null) { r.options = []; return } }
            return
          }
          const opts = presetDataMap.get(Number(presetId)) || presetDataMap.get(String(presetId))
          if (!opts) return
          const rules = designer.getRule()
          for (const r of rules) {
            if (r.itsmPresetId === presetId || r.itsmPresetId === Number(presetId)) {
              r.options = JSON.parse(JSON.stringify(opts))
              return
            }
          }
        },
      },
    }], true)
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
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}
.fc-itsm-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 560px;
  color: #909399;
  font-size: 14px;
}
.fc-itsm-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
}
</style>
