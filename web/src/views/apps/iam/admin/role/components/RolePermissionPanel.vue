<template>
  <el-dialog v-model="visible" title="权限配置" width="860px" top="5vh" destroy-on-close append-to-body @closed="$emit('closed')">
    <template #header>
      <div style="display:flex;align-items:center;gap:12px">
        <span>权限配置</span>
        <el-tag type="primary" effect="dark" round size="small">{{ roleName }}</el-tag>
        <el-button type="primary" size="small" :loading="saving" @click="handleSave" style="margin-left:auto">保存权限</el-button>
      </div>
    </template>

    <div class="rpp-body" v-loading="loading">
      <el-empty v-if="!loading && !catalog.length" description="暂无权限数据" :image-size="60" />

      <template v-else>
        <!-- App selector -->
        <div class="rpp-app-tabs">
          <div v-for="app in catalog" :key="app.app"
            class="rpp-app-tab"
            :class="{ active: selectedApp === app.app }"
            @click="selectedApp = app.app">
            {{ appLabel(app.app) }}
          </div>
        </div>

        <!-- Permission checkboxes -->
        <div v-if="currentTabs.length" class="rpp-perm-list">
          <div v-for="tab in currentTabs" :key="tab.key" class="rpp-perm-row">
            <div class="rpp-perm-module">
              <el-icon v-if="iconMap[tab.icon]" size="15"><component :is="iconMap[tab.icon]" /></el-icon>
              <span>{{ isEn ? tab.label_en : tab.label_zh }}</span>
              <span v-if="tab.required_perm_tab" class="rpp-perm-key">{{ tab.required_perm_tab.split(':').slice(1).join(':') }}</span>
            </div>
            <div class="rpp-perm-action">
              <template v-if="tab.buttons.length || tab.required_perm_tab">
                <el-checkbox-group v-model="selectedPerms" class="rpp-perm-group">
                  <el-checkbox v-for="btn in tab.buttons" :key="btn.key"
                    :value="btn.required_perm" size="small" class="rpp-perm-cb">
                    {{ isEn ? btn.label_en : btn.label_zh }}
                  </el-checkbox>
                  <el-checkbox v-if="tab.required_perm_tab && !tab.buttons.length"
                    :value="tab.required_perm_tab" size="small">授予访问权限</el-checkbox>
                </el-checkbox-group>
                <div v-if="tab.required_perm_tab && tab.buttons.length" class="rpp-perm-hint">
                  + 自动包含 <code>{{ tab.required_perm_tab.split(':').slice(1).join(':') }}</code>
                </div>
              </template>
              <span v-else class="rpp-perm-open">默认开放</span>
            </div>
          </div>
        </div>

        <div v-if="selectedPerms.length" class="rpp-selected-count">
          已选 <el-tag size="small" type="primary">{{ selectedPerms.length }}</el-tag> 项
        </div>
      </template>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { request } from '/@/utils/service'

const props = defineProps<{ modelValue: boolean; roleId: number; roleName: string }>()
const emit = defineEmits(['update:modelValue', 'closed'])

const visible = ref(props.modelValue)
watch(() => props.modelValue, v => { visible.value = v; if (v) loadData() })
watch(visible, v => emit('update:modelValue', v))

const loading = ref(false)
const saving = ref(false)
const catalog = ref<any[]>([])
const selectedApp = ref('opsflow')
const selectedPerms = ref<string[]>([])
const isEn = computed(() => String(document.documentElement.lang || '').startsWith('en'))

const iconMap: Record<string, any> = {}

const currentTabs = computed(() =>
  catalog.value.find((a: any) => a.app === selectedApp.value)?.tabs || []
)

function appLabel(app: string) {
  const map: Record<string, string> = { opsflow: 'OPSflow', itsm: 'ITSM', cmdb: 'CMDB' }
  return map[app] || app
}

async function loadData() {
  loading.value = true
  try {
    const [catRes, permRes] = await Promise.all([
      request({ url: '/api/iam/permission-catalog/', method: 'get' }),
      request({ url: `/api/iam/role/${props.roleId}/permissions/`, method: 'get' }),
    ])
    catalog.value = catRes?.data || []
    selectedPerms.value = permRes?.data || []
    if (catalog.value.length) selectedApp.value = catalog.value[0].app
  } catch { catalog.value = []; selectedPerms.value = [] }
  loading.value = false
}

async function handleSave() {
  saving.value = true
  try {
    const res = await request({
      url: `/api/iam/role/${props.roleId}/permissions/`,
      method: 'post',
      data: { permissions: selectedPerms.value },
    })
    if (res?.code === 2000) {
      ElMessage.success('权限保存成功')
      visible.value = false
    } else {
      ElMessage.error(res?.msg || '保存失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.msg || '保存失败')
  }
  saving.value = false
}
</script>

<style scoped lang="scss">
.rpp-body { min-height: 400px; }

.rpp-app-tabs {
  display: flex; gap: 4px; margin-bottom: 14px; flex-wrap: wrap;
}
.rpp-app-tab {
  padding: 6px 16px; font-size: 13px; font-weight: 500; color: #606266;
  background: #f5f7fa; border-radius: 8px; cursor: pointer;
  &:hover { background: #ecf5ff; color: #409eff; }
  &.active { color: #fff; background: #409eff; }
}

.rpp-perm-list {
  border: 1px solid #ebeef5; border-radius: 10px; overflow: hidden;
}
.rpp-perm-row {
  display: flex; align-items: flex-start; padding: 10px 14px;
  & + & { border-top: 1px solid #f0f0f0; }
  &:hover { background: #fafbfc; }
}
.rpp-perm-module {
  flex: 0 0 220px; display: flex; align-items: center; gap: 6px; min-height: 28px;
  .el-icon { color: #909399; flex-shrink: 0; }
}
.rpp-perm-key {
  font-size: 10px; font-family: monospace; color: #999; background: #f0f0f0;
  padding: 1px 6px; border-radius: 4px; white-space: nowrap;
}
.rpp-perm-action { flex: 1; }
.rpp-perm-group { display: flex; flex-wrap: wrap; gap: 6px; }
.rpp-perm-cb { margin-right: 0 !important; }
.rpp-perm-hint { font-size: 11px; color: #bbb; margin-top: 2px; width: 100%; code { font-size: 10px; background: #f5f5f5; padding: 1px 5px; border-radius: 3px; color: #999; } }
.rpp-perm-open { font-size: 12px; color: #c0c4cc; line-height: 28px; }
.rpp-selected-count { margin-top: 12px; font-size: 13px; color: #606266; }
</style>
