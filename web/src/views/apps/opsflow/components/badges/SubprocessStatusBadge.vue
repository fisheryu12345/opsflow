<template>
  <div v-if="staleCount > 0" class="subprocess-status-badge">
    <el-badge :value="staleCount" :max="99" type="danger">
      <el-button size="small" :icon="Refresh" @click="showDialog = true">
        Subprocess Updates
      </el-button>
    </el-badge>

    <el-dialog v-model="showDialog" title="Subprocess Version Updates" width="580px" top="15vh">
      <div v-if="loading" v-loading="loading" style="min-height:80px" />
      <template v-else>
        <div v-if="details.length === 0" class="dialog-empty">
          <el-empty description="No subprocess references found" :image-size="40" />
        </div>
        <div v-for="d in details" :key="d.node_id" class="subproc-row">
          <div class="subproc-info">
            <strong>{{ d.target_name || 'Unknown' }}</strong>
            <code class="subproc-node">{{ d.node_id }}</code>
          </div>
          <div class="subproc-versions">
            <el-tag v-if="d.stale" type="warning" size="small" effect="dark">
              v{{ d.referenced_version || '?' }} → v{{ d.current_version || '?' }}
            </el-tag>
            <el-tag v-else type="success" size="small" effect="plain">
              v{{ d.current_version || '?' }}
            </el-tag>
          </div>
        </div>
      </template>
      <template #footer>
        <el-button @click="showDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="updating" :disabled="staleCount === 0" @click="batchUpdate">
          Update All ({{ staleCount }})
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { GetSubprocessStatus, UpdateSubprocessRefs } from '../../api/templates'

const props = defineProps<{ templateId: number | null }>()
const emit = defineEmits<{ updated: [] }>()

const details = ref<any[]>([])
const showDialog = ref(false)
const loading = ref(false)
const updating = ref(false)

const staleCount = computed(() => details.value.filter((d: any) => d.stale).length)

async function fetchStatus() {
  if (!props.templateId) return
  loading.value = true
  try {
    const res = await GetSubprocessStatus(props.templateId)
    details.value = res.data?.data?.details || []
  } catch { details.value = [] }
  loading.value = false
}

async function batchUpdate() {
  if (!props.templateId) return
  updating.value = true
  try {
    await UpdateSubprocessRefs(props.templateId)
    ElMessage.success(`Updated ${staleCount.value} subprocess references`)
    showDialog.value = false
    emit('updated')
  } catch (e: any) {
    ElMessage.error(e?.msg || 'Update failed')
  }
  updating.value = false
}

watch(() => props.templateId, fetchStatus)
onMounted(fetchStatus)
</script>

<style lang="scss" scoped>
@use '../../styles/opsflow-global' as *;

.subprocess-status-badge {
  position: absolute;
  top: 12px;
  /* left handled by inline style in DesignCanvas for spacing */
  z-index: 101;
}
.subproc-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}
.subproc-row:last-child { border-bottom: none; }
.subproc-info { display: flex; flex-direction: column; gap: 2px; }
.subproc-node { font-size: 11px; color: #909399; font-family: monospace; }
.subproc-versions { flex-shrink: 0; }
.dialog-empty { padding: 20px 0; }
</style>
