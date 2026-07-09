<template>
  <el-form-item :label="$t('message.designer.processor')">
    <!-- Preset mode: dropdown filtered by preset type -->
    <el-select
      v-show="node._usePreset"
      :model-value="node.preset_id"
      @update:model-value="onPresetSelect"
      filterable clearable size="small" style="width:100%"
      :placeholder="$t('message.preset.selectPreset')"
    >
      <el-option
        v-for="p in filteredPresets"
        :key="p.id" :label="p.name" :value="p.id"
      />
    </el-select>

    <!-- Manual mode: user multi-select (PERSON type) -->
    <el-select
      v-if="inputMode === 'select'"
      v-show="!node._usePreset"
      :model-value="personUsers"
      @update:model-value="$emit('update:personUsers', $event)"
      multiple filterable size="small" style="width:100%"
      :loading="usersLoading"
      :placeholder="manualPlaceholder"
      @focus="$emit('loadUsers')"
      @change="$emit('personChange')"
    >
      <el-option
        v-for="u in userOptions"
        :key="u.value"
        :label="u.label"
        :value="u.value"
      />
    </el-select>

    <!-- Manual mode: text input (ROLE / ORGANIZATION) -->
    <el-input
      v-if="inputMode === 'text'"
      v-show="!node._usePreset"
      :model-value="node.processorsRaw"
      @update:model-value="onProcessorsRawChange"
      :placeholder="manualPlaceholder"
    />

    <!-- Toggle preset / manual -->
    <div style="text-align:right;margin-top:3px">
      <el-button link size="small" type="primary" @click="onToggle">
        {{ node._usePreset ? $t('message.preset.switchManual') : $t('message.preset.switchPreset') }}
      </el-button>
    </div>
  </el-form-item>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
  presetType: string           // 'user_list' | 'role_list' | 'dept_list'
  inputMode: 'select' | 'text' // manual input type
  node: any                    // current workflow node
  personUsers: string[]        // multi-select user array (select mode)
  userOptions: any[]           // user search dropdown options
  usersLoading: boolean        // user search loading state
  presetOptions: any[]         // all presets (filtered internally)
  manualPlaceholder: string    // placeholder for manual input
}>()

const emit = defineEmits<{
  'update:personUsers': [value: string[]]
  loadUsers: []
  personChange: []
  change: []
}>()

const filteredPresets = computed(() =>
  props.presetOptions.filter((o: any) => o.preset_type === props.presetType)
)

function onPresetSelect(val: any) {
  props.node.preset_id = val || null
  emit('change')
}

function onProcessorsRawChange(val: string) {
  props.node.processorsRaw = val
  emit('change')
}

function onToggle() {
  if (!props.node) return
  props.node._usePreset = !props.node._usePreset
  if (props.node._usePreset) {
    // Switching to preset mode: clear manual inputs
    props.node.processorsRaw = ''
    emit('update:personUsers', [])
  } else {
    // Switching to manual mode: clear preset selection
    props.node.preset_id = null
  }
  emit('change')
}
</script>
