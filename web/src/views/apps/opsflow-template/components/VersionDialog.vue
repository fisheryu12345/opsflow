<template>
  <el-dialog :model-value="visible" @update:model-value="emit('update:visible', $event)"
    :title="'版本历史: ' + displayName" width="600px" top="8vh" destroy-on-close>
    <div v-loading="loading">
      <el-timeline v-if="versions.length">
        <el-timeline-item v-for="v in versions" :key="v.id" :timestamp="v.created_at" placement="top">
          <div class="version-item">
            <div class="version-header">
              <el-tag size="small" type="primary" effect="dark">V{{ v.version }}</el-tag>
              <span class="version-note" v-if="v.created_by_name">by {{ v.created_by_name }}</span>
            </div>
            <div class="version-actions">
              <el-button size="small" text type="primary" @click="handleRollback(v)" :disabled="v.version === currentVersion">
                {{ v.version === currentVersion ? '当前版本' : '回滚到此版本' }}
              </el-button>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else-if="!loading" description="暂无版本历史" />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GetTemplateVersions, RollbackTemplate } from '/@/api/opsflow/templates'

const props = withDefaults(defineProps<{
  visible?: boolean
  templateId?: number | null
  templateName?: string
  currentVersion?: number
}>(), { visible: false, templateId: null, templateName: '' })

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'rolled-back'): void
}>()

const loading = ref(false)
const versions = ref<any[]>([])
const displayName = computed(() => {
  const name = props.templateName || ''
  return name.length > 20 ? name.slice(0, 20) + '…' : name
})

watch(() => props.visible, async (v) => {
  if (v && props.templateId) {
    loading.value = true
    try {
      const res = await GetTemplateVersions(props.templateId)
      versions.value = res.data || []
    } catch {
      versions.value = []
    }
    loading.value = false
  }
})

async function handleRollback(v: any) {
  try {
    await ElMessageBox.confirm(`确定回滚到 V${v.version}？当前未发布的修改将丢失。`, '确认回滚', {
      confirmButtonText: '确认回滚',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await RollbackTemplate(props.templateId!, v.version)
    ElMessage.success(`已回滚到 V${v.version}`)
    emit('rolled-back')
    emit('update:visible', false)
  } catch {
    // cancelled
  }
}
</script>

<style scoped>
.version-item { display: flex; flex-direction: column; gap: 6px; }
.version-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.version-note { font-size: 13px; color: #303133; }
.version-by { font-size: 11px; color: #909399; }
.version-actions { padding-left: 0; }
</style>
