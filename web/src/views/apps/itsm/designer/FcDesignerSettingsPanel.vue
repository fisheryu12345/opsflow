<template>
  <el-drawer
    :model-value="visible"
    direction="ltr"
    size="350px"
    title="设计器设置"
    @close="$emit('close')"
  >
    <template #default>
      <div class="settings-body">
        <!-- ── 左侧边栏 ── -->
        <div class="settings-group">
          <div class="settings-group-title">左侧边栏</div>
          <div class="settings-row">
            <span>多语言板块</span>
            <el-switch v-model="cfg.showLanguage" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>JSON预览板块</span>
            <el-switch v-model="cfg.showJsonPreview" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>多端切换按钮</span>
            <el-switch v-model="cfg.showDevice" size="small" @change="onChange" />
          </div>
        </div>

        <el-divider />

        <!-- ── 顶部工具栏 ── -->
        <div class="settings-group">
          <div class="settings-group-title">顶部工具栏</div>
          <div class="settings-row">
            <span>预览按钮</span>
            <el-switch v-model="cfg.showPreviewBtn" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>默认值按钮</span>
            <el-switch v-model="cfg.showInputData" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>右侧配置栏</span>
            <el-switch v-model="cfg.showConfig" size="small" @change="onChange" />
          </div>
        </div>

        <el-divider />

        <!-- ── 功能开关 ── -->
        <div class="settings-group">
          <div class="settings-group-title">功能开关</div>
          <div class="settings-row">
            <span>快捷键</span>
            <el-switch v-model="cfg.hotKey" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>复制组件时自动重置编码</span>
            <el-switch v-model="cfg.autoResetField" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>字段ID可编辑</span>
            <el-switch v-model="fieldEditable" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>组件编码可编辑</span>
            <el-switch v-model="nameEditable" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>隐藏组件操作按钮</span>
            <el-switch v-model="cfg.hiddenDragMenu" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>隐藏组件拖拽</span>
            <el-switch v-model="cfg.hiddenDragBtn" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>关闭页面时确认弹窗</span>
            <el-switch v-model="cfg.exitConfirm" size="small" @change="onChange" />
          </div>
        </div>

        <el-divider />

        <!-- ── 配置开关 ── -->
        <div class="settings-group">
          <div class="settings-group-title">配置开关</div>
          <div class="settings-row">
            <span>表单配置</span>
            <el-switch v-model="cfg.showFormConfig" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>组件编码</span>
            <el-switch v-model="cfg.showComponentName" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>组件基础配置</span>
            <el-switch v-model="cfg.showBaseForm" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>组件联动配置</span>
            <el-switch v-model="cfg.showControl" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>组件自定义属性按钮</span>
            <el-switch v-model="cfg.showCustomProps" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>组件属性配置</span>
            <el-switch v-model="cfg.showPropsForm" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>组件样式配置</span>
            <el-switch v-model="cfg.showStyleForm" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>组件事件配置</span>
            <el-switch v-model="cfg.showEventForm" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>组件验证配置</span>
            <el-switch v-model="cfg.showValidateForm" size="small" @change="onChange" />
          </div>
          <div class="settings-row">
            <span>只显示组件必填验证</span>
            <el-switch v-model="cfg.validateOnlyRequired" size="small" @change="onChange" />
          </div>
        </div>

        <el-divider />

        <!-- ── 菜单设置 ── -->
        <div class="settings-group">
          <div class="settings-group-title">菜单设置</div>
          <div v-for="g in menuGroups" :key="g.name" class="menu-group">
            <div class="settings-row menu-group-header">
              <span>{{ g.label }}</span>
              <el-switch :model-value="menuVisible(g.name)" size="small" @change="(v:boolean) => toggleMenu(g.name, v)" />
            </div>
            <div v-if="menuVisible(g.name)" class="menu-group-items">
              <div v-for="item in g.items" :key="item.name" class="settings-row menu-item-row">
                <span>{{ item.label }}</span>
                <el-checkbox :model-value="itemVisible(item.name)" size="small" @change="(v:boolean) => toggleItem(item.name, v)" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template #footer>
      <div class="settings-footer">
        <el-button @click="handleReset">重置默认</el-button>
        <el-button type="primary" @click="$emit('close')">关闭</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  designerConfig,
  saveDesignerSettings,
  resetDesignerSettings,
  MENU_GROUPS,
} from './fcExtensions'

defineProps<{ visible: boolean }>()
defineEmits<{ close: [] }>()

const cfg = designerConfig
const menuGroups = MENU_GROUPS

// Inverted toggles: fieldEditable = !fieldReadonly
const fieldEditable = computed({
  get: () => !(cfg as any).fieldReadonly,
  set: (v: boolean) => { (cfg as any).fieldReadonly = !v; saveDesignerSettings() },
})
const nameEditable = computed({
  get: () => !(cfg as any).nameReadonly,
  set: (v: boolean) => { (cfg as any).nameReadonly = !v; saveDesignerSettings() },
})

// hiddenMenu: master switch per group — visible = group NOT in hiddenMenu
function menuVisible(group: string): boolean {
  const hm: string[] = (cfg as any).hiddenMenu || []
  return !hm.includes(group)
}

function toggleMenu(group: string, visible: boolean) {
  let hm: string[] = (cfg as any).hiddenMenu || []
  if (visible) {
    hm = hm.filter((g: string) => g !== group)
  } else {
    if (!hm.includes(group)) hm = [...hm, group]
  }
  (cfg as any).hiddenMenu = hm
  saveDesignerSettings()
}

// hiddenItem: per-component checkbox — visible = component NOT in hiddenItem
function itemVisible(name: string): boolean {
  const hi: string[] = (cfg as any).hiddenItem || []
  return !hi.includes(name)
}

function toggleItem(name: string, visible: boolean) {
  let hi: string[] = (cfg as any).hiddenItem || []
  if (visible) {
    hi = hi.filter((n: string) => n !== name)
  } else {
    if (!hi.includes(name)) hi = [...hi, name]
  }
  ;(cfg as any).hiddenItem = hi
  saveDesignerSettings()
}

function onChange() {
  saveDesignerSettings()
}

function handleReset() {
  ;(cfg as any).hiddenMenu = []
  ;(cfg as any).hiddenItem = []
  resetDesignerSettings()
}
</script>

<style scoped>
.settings-body { padding: 0 4px; }
.settings-group { margin-bottom: 4px; }
.settings-group-title {
  font-size: 13px; font-weight: 600; color: #303133; margin-bottom: 8px;
}
.settings-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0; font-size: 13px; color: #606266;
}
.settings-footer { display: flex; justify-content: space-between; }
.menu-group { margin-bottom: 4px; }
.menu-group-header { font-weight: 500; }
.menu-group-items {
  margin-left: 4px; padding: 4px 8px;
  border-left: 2px solid #ebeef5;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px 8px;
}
.menu-item-row span { font-size: 12px; color: #909399; }
.menu-item-row { padding: 2px 0; }
</style>
