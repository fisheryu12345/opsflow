<template>
  <div>
    <div class="itsm-table-card">
      <div class="itsm-table-header">
        <span class="itsm-table-title">{{ $t('message.itsmPage.slaPolicies') }}</span>
      </div>
      <el-table :data="items" v-loading="loading" stripe style="width:100%" size="small"
        :empty-text="loading ? $t('message.itsmPage.loading') : $t('message.itsmPage.noSla')">
        <el-table-column prop="name" :label="$t('message.itsmPage.colSLAPolicy')" min-width="160" />
        <el-table-column prop="priority" :label="$t('message.ticketCreate.priority')" width="80" />
        <el-table-column prop="response_minutes" :label="$t('message.itsmPage.colResponseMin')" width="140" />
        <el-table-column prop="resolve_minutes" :label="$t('message.itsmPage.colResolveMin')" width="140" />
        <el-table-column prop="is_active" :label="$t('message.itsmPage.colEnabled')" width="80" align="center">
          <template #default="{ row }"><el-switch v-model="row.is_active" size="small" @change="onToggle(row)" /></template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colActions')" width="80" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text v-can="'itsm:sla:edit'" @click="onEdit(row)">{{ $t('message.common.edit') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="showEdit" :title="$t('message.itsmPage.editSlaPolicy')" width="440px" top="15vh" destroy-on-close append-to-body>
      <el-form :model="form" label-width="120px" size="small">
        <el-form-item :label="$t('message.itsmPage.colSLAPolicy')"><el-input v-model="form.name" /></el-form-item>
        <el-form-item :label="$t('message.ticketCreate.priority')" v-if="!form.id">
          <el-select v-model="form.priority" style="width:100%">
            <el-option label="P1" value="P1" /><el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" /><el-option label="P4" value="P4" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.ticketCreate.priority')" v-else>
          <span style="font-weight:600">{{ form.priority }}</span>
        </el-form-item>
        <el-form-item :label="$t('message.itsmPage.responseMinLabel')"><el-input-number v-model="form.response_minutes" :min="1" :max="10080" style="width:160px" /></el-form-item>
        <el-form-item :label="$t('message.itsmPage.resolveMinLabel')"><el-input-number v-model="form.resolve_minutes" :min="1" :max="43200" style="width:160px" /></el-form-item>
        <el-form-item :label="$t('message.itsmPage.colEnabled')"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">{{ $t('message.common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { slaPolicyApi } from '/@/api/itsm/index'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const { reportStats: updateHeroStats } = useHeroConsumer()

const loading = ref(false)
const items = ref<any[]>([])

const showEdit = ref(false)
const saving = ref(false)
const form = ref<any>({ name: '', priority: 'P3', response_minutes: 60, resolve_minutes: 480, is_active: true })

async function loadItems() {
  loading.value = true
  try { const res = await slaPolicyApi.list(); items.value = res?.results || res?.data || res || []; reportStats() } finally { loading.value = false }
}

function reportStats() {
  updateHeroStats([
    { value: items.value.length, label: '策略总数' },
    { value: items.value.filter((s: any) => s.is_active).length, label: '已启用' },
  ])
}

function onEdit(row: any) {
  form.value = { ...row }
  showEdit.value = true
}

async function onSave() {
  saving.value = true
  try {
    const { id, name, response_minutes, resolve_minutes, is_active } = form.value
    await slaPolicyApi.update(id, { name, response_minutes, resolve_minutes, is_active })
    ElMessage.success('保存成功')
    showEdit.value = false
    await loadItems()
  } catch { ElMessage.error('保存失败') }
  saving.value = false
}

async function onToggle(row: any) {
  try { await slaPolicyApi.update(row.id, { is_active: row.is_active }) } catch { row.is_active = !row.is_active }
}

onMounted(() => {
  if (props.active) loadItems()
})

watch(() => props.active, (isActive) => {
  if (isActive && items.value.length === 0) loadItems()
})
</script>
