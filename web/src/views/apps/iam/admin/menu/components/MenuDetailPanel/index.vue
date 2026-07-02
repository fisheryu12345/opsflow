<template>
  <div class="menu-detail-panel">
    <!-- Empty state -->
    <div v-if="!menu" class="mdp-empty">
      <el-empty :image-size="60">
        <template #description>
          <span class="mdp-empty-text">{{ t('message.menuPage.selectMenuPrompt') }}</span>
        </template>
      </el-empty>
    </div>

    <!-- Detail -->
    <template v-else>
      <!-- ═══ Header: Icon + Name + Actions ═══ -->
      <div class="mdp-header">
        <div class="mdp-header-left">
          <el-popover placement="bottom-start" :width="620" trigger="click" popper-class="mdp-icon-popover">
            <template #reference>
              <div class="mdp-icon-wrap" :title="t('message.menuPage.clickChangeIcon')">
                <SvgIcon v-if="menu.icon" :name="menu.icon" class="mdp-icon-lg" />
                <el-icon v-else :size="24"><Menu /></el-icon>
                <div class="mdp-icon-badge">
                  <el-icon :size="10"><EditPen /></el-icon>
                </div>
              </div>
            </template>
            <div class="mdp-icon-picker-inner">
              <div class="mdp-icon-picker-title">{{ t('message.menuPage.icon') }}</div>
              <IconSelector v-model="iconModel" />
            </div>
          </el-popover>
          <div class="mdp-header-text">
            <div class="mdp-title-row">
              <span class="mdp-title">{{ menu.name }}</span>
              <el-tag v-if="menu.is_catalog" size="small" type="warning" effect="plain">{{ t('message.menuPage.catalogTag') }}</el-tag>
            </div>
            <div class="mdp-subtitle">{{ menu.name_en || menu.web_path }}</div>
          </div>
        </div>
        <div class="mdp-header-actions">
          <el-button size="small" @click="$emit('edit', menu)">
            <el-icon><Edit /></el-icon> {{ t('message.menuPage.editMenu') }}
          </el-button>
          <el-button size="small" type="danger" @click="$emit('delete', menu)">
            <el-icon><Delete /></el-icon> {{ t('message.menuPage.deleteMenu') }}
          </el-button>
        </div>
      </div>

      <!-- ═══ Basic Info ═══ -->
      <div class="mdp-card">
        <div class="mdp-card-header">{{ t('message.menuPage.basicInfo') }}</div>
        <div class="mdp-card-body mdp-grid-3">
          <div class="mdp-field">
            <div class="mdp-label">{{ t('message.menuPage.icon') }}</div>
            <div class="mdp-value-icon">
              <SvgIcon v-if="menu.icon" :name="menu.icon" class="mdp-icon-sm" />
              <code class="mdp-code">{{ menu.icon }}</code>
            </div>
          </div>
          <div class="mdp-field">
            <div class="mdp-label">{{ t('message.menuPage.nameEn') }}</div>
            <div class="mdp-value">{{ menu.name_en || '-' }}</div>
          </div>
          <div class="mdp-field">
            <div class="mdp-label">{{ t('message.menuPage.parentMenu') }}</div>
            <div class="mdp-value">{{ parentName || '-' }}</div>
          </div>
          <div class="mdp-field">
            <div class="mdp-label">{{ t('message.menuPage.sort') }}</div>
            <div class="mdp-value-sort">
              <span class="mdp-sort-num">{{ menu.sort }}</span>
              <div class="mdp-sort-btns">
                <el-button size="small" :icon="Top" circle @click="moveUp" :disabled="sorting" />
                <el-button size="small" :icon="Bottom" circle @click="moveDown" :disabled="sorting" />
              </div>
            </div>
          </div>
          <div class="mdp-field">
            <div class="mdp-label">{{ t('message.menuPage.id') }}</div>
            <div class="mdp-value"><code class="mdp-code">{{ menu.id }}</code></div>
          </div>
        </div>
      </div>

      <!-- ═══ Route & Component ═══ -->
      <div class="mdp-card">
        <div class="mdp-card-header">{{ t('message.menuPage.routeInfo') }}</div>
        <div class="mdp-card-body mdp-grid-2">
          <div class="mdp-field">
            <div class="mdp-label">{{ t('message.menuPage.routePath') }}</div>
            <div class="mdp-value"><code class="mdp-code mdp-code-path">{{ menu.web_path }}</code></div>
          </div>
          <div class="mdp-field">
            <div class="mdp-label">{{ t('message.menuPage.component') }}</div>
            <div class="mdp-value"><code class="mdp-code">{{ menu.component || '-' }}</code></div>
          </div>
          <div class="mdp-field">
            <div class="mdp-label">{{ t('message.menuPage.componentName') }}</div>
            <div class="mdp-value"><code class="mdp-code">{{ menu.component_name || '-' }}</code></div>
          </div>
          <div class="mdp-field">
            <div class="mdp-label">{{ t('message.menuPage.linkUrl') }}</div>
            <div class="mdp-value mdp-value-muted">{{ menu.link_url || '-' }}</div>
          </div>
        </div>
      </div>

      <!-- ═══ Toggles ═══ -->
      <div class="mdp-card">
        <div class="mdp-card-header">{{ t('message.menuPage.toggles') }}</div>
        <div class="mdp-card-body">
          <div class="mdp-toggles">
            <div class="mdp-toggle-item">
              <span class="mdp-toggle-label">{{ t('message.menuPage.status') }}</span>
              <el-switch :model-value="menu.status" @change="(v: boolean) => toggleField('status', v)" :loading="toggling === 'status'" />
            </div>
            <div class="mdp-toggle-item">
              <span class="mdp-toggle-label">{{ t('message.menuPage.sidebar') }}</span>
              <el-switch :model-value="menu.visible" @change="(v: boolean) => toggleField('visible', v)" :loading="toggling === 'visible'" />
            </div>
            <div class="mdp-toggle-item">
              <span class="mdp-toggle-label">{{ t('message.menuPage.cache') }}</span>
              <el-switch :model-value="menu.cache" @change="(v: boolean) => toggleField('cache', v)" :loading="toggling === 'cache'" />
            </div>
            <div class="mdp-toggle-item">
              <span class="mdp-toggle-label">{{ t('message.menuPage.isCatalog') }}</span>
              <el-switch :model-value="menu.is_catalog" @change="(v: boolean) => toggleField('is_catalog', v)" :loading="toggling === 'is_catalog'" />
            </div>
            <div class="mdp-toggle-item">
              <span class="mdp-toggle-label">{{ t('message.menuPage.isLink') }}</span>
              <el-switch :model-value="menu.is_link" @change="(v: boolean) => toggleField('is_link', v)" :loading="toggling === 'is_link'" />
            </div>
            <div class="mdp-toggle-item">
              <span class="mdp-toggle-label">{{ t('message.menuPage.isIframe') }}</span>
              <el-switch :model-value="menu.is_iframe" @change="(v: boolean) => toggleField('is_iframe', v)" :loading="toggling === 'is_iframe'" />
            </div>
          </div>
          <div class="mdp-toggle-hint">{{ t('message.menuPage.toggleHint') }}</div>
        </div>
      </div>

      <!-- ═══ Description ═══ -->
      <div class="mdp-card mdp-card-last">
        <div class="mdp-card-header">{{ t('message.menuPage.description') }}</div>
        <div class="mdp-card-body">
          <p class="mdp-desc-text">{{ menu.description || '-' }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Edit, Delete, Menu, EditPen, Top, Bottom } from '@element-plus/icons-vue'
import SvgIcon from '/@/components/svgIcon/index.vue'
import IconSelector from '/@/components/iconSelector/index.vue'
import { UpdateObj, menuMoveUp, menuMoveDown } from '../../api'
import type { MenuTreeItemType } from '../../types'

const { t } = useI18n()

interface IProps {
  menu: MenuTreeItemType | null
  treeData: MenuTreeItemType[]
}
const props = withDefaults(defineProps<IProps>(), {
  menu: null,
  treeData: () => [],
})
const emit = defineEmits<{
  edit: [menu: MenuTreeItemType]
  delete: [menu: MenuTreeItemType]
  refresh: []
}>()

/* ── Icon selector (v-model sync) ── */
const iconModel = computed({
  get: () => props.menu?.icon || '',
  set: async (val: string) => {
    if (!props.menu?.id) return
    try {
      await UpdateObj({ id: props.menu.id, icon: val })
      ElMessage.success(t('message.menuPage.saveSuccess'))
      emit('refresh')
    } catch {
      ElMessage.error(t('message.menuPage.saveFailed'))
    }
  },
})

/* ── Parent name resolver ── */
const parentName = computed(() => {
  if (!props.menu?.parent) return null
  const walk = (nodes: MenuTreeItemType[]): string | null => {
    for (const n of nodes) {
      if (String(n.id) === String(props.menu!.parent)) return n.name
      if (n.children?.length) {
        const found = walk(n.children)
        if (found) return found
      }
    }
    return null
  }
  return walk(props.treeData)
})

/* ── Inline toggles ── */
const toggling = ref<string | null>(null)

async function toggleField(field: string, val: boolean) {
  if (!props.menu?.id) return
  toggling.value = field
  try {
    await UpdateObj({ id: props.menu.id, [field]: val })
    emit('refresh')
  } catch {
    ElMessage.error(t('message.menuPage.saveFailed'))
  } finally {
    toggling.value = null
  }
}

/* ── Sort ── */
const sorting = ref(false)

async function moveUp() {
  if (!props.menu?.id || sorting.value) return
  sorting.value = true
  try {
    await menuMoveUp({ menu_id: props.menu.id })
    emit('refresh')
  } catch {
    ElMessage.error(t('message.menuPage.sortFailed'))
  } finally {
    sorting.value = false
  }
}

async function moveDown() {
  if (!props.menu?.id || sorting.value) return
  sorting.value = true
  try {
    await menuMoveDown({ menu_id: props.menu.id })
    emit('refresh')
  } catch {
    ElMessage.error(t('message.menuPage.sortFailed'))
  } finally {
    sorting.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

/* ═══════════════════ Wrapper ═══════════════════ */
.menu-detail-panel {
  height: 100%;
  overflow-y: auto;
  padding: 16px 18px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* ── Empty ── */
.mdp-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mdp-empty-text {
  font-size: 13px;
  color: #c0c4cc;
}

/* ═══════════════════ Header ═══════════════════ */
.mdp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid $g-border-light;
}
.mdp-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  flex: 1;
}
.mdp-icon-wrap {
  position: relative;
  width: 48px;
  height: 48px;
  background: #ecf5ff;
  border: 2px dashed #c6e2ff;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color 0.15s;
  &:hover {
    border-color: $g-color-primary;
  }
}
.mdp-icon-lg {
  font-size: 24px;
  color: $g-color-primary;
}
.mdp-icon-badge {
  position: absolute;
  bottom: -4px;
  right: -4px;
  width: 18px;
  height: 18px;
  background: $g-color-primary;
  border: 2px solid #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.mdp-header-text {
  min-width: 0;
}
.mdp-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}
.mdp-title {
  font-size: 18px;
  font-weight: 700;
  color: $g-text-primary;
}
.mdp-subtitle {
  font-size: 12px;
  color: $g-text-secondary;
  font-family: 'SF Mono', 'Cascadia Code', Menlo, monospace;
}
.mdp-header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* ═══════════════════ Cards ═══════════════════ */
.mdp-card {
  background: $g-bg-card;
  border: 1px solid $g-border-card;
  border-radius: $g-radius-sm;
  overflow: hidden;
}
.mdp-card-last {
  flex: 1;
}
.mdp-card-header {
  padding: 8px 14px;
  background: #f5f7fa;
  border-bottom: 1px solid $g-border-light;
  font-size: 12px;
  font-weight: 600;
  color: $g-text-secondary;
}
.mdp-card-body {
  padding: 14px;
}

/* ── Grids ── */
.mdp-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 20px;
}
.mdp-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px 20px;
}

/* ── Fields ── */
.mdp-field {
  min-width: 0;
}
.mdp-label {
  font-size: 11px;
  color: $g-text-muted;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.mdp-value {
  font-size: 13px;
  color: $g-text-primary;
  word-break: break-all;
}
.mdp-value-muted {
  color: $g-text-muted;
  font-style: italic;
}
.mdp-code {
  font-size: 12px;
  font-family: 'SF Mono', 'Cascadia Code', Menlo, monospace;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
  color: $g-color-primary;
}
.mdp-code-path {
  font-weight: 600;
}

/* ── Icon in field ── */
.mdp-value-icon {
  display: flex;
  align-items: center;
  gap: 6px;
}
.mdp-icon-sm {
  font-size: 18px;
  color: $g-color-primary;
}

/* ── Sort ── */
.mdp-value-sort {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mdp-sort-num {
  font-size: 18px;
  font-weight: 700;
  color: $g-text-primary;
  min-width: 24px;
}
.mdp-sort-btns {
  display: flex;
  flex-direction: row;
  gap: 4px;
}

/* ═══════════════════ Toggles ═══════════════════ */
.mdp-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 14px 24px;
}
.mdp-toggle-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 130px;
}
.mdp-toggle-label {
  font-size: 13px;
  color: $g-text-primary;
  min-width: 70px;
}
.mdp-toggle-hint {
  margin-top: 12px;
  font-size: 11px;
  color: $g-text-muted;
  font-style: italic;
}

/* ── Description ── */
.mdp-desc-text {
  margin: 0;
  font-size: 13px;
  color: $g-text-secondary;
  line-height: 1.7;
  white-space: pre-wrap;
}
</style>

<style lang="scss">
/* ── Icon popover ── */
.mdp-icon-popover {
  width: 600px !important;
  padding: 16px;

  .icon-selector-warp {
    max-height: 400px;
    overflow-y: auto;
  }
  .icon-selector-warp-title {
    margin-bottom: 6px;
  }
  .el-tabs__item {
    font-size: 13px;
    padding: 0 16px !important;
  }
  .icon-selector-warp-row .el-col {
    flex: 0 0 20% !important;
    max-width: 20% !important;
  }
  .icon-selector {
    min-width: 560px;
  }
}

/* Force inner IconSelector popover to be wide enough */
.icon-selector-popper {
  width: 580px !important;
  padding: 12px !important;
}
</style>
