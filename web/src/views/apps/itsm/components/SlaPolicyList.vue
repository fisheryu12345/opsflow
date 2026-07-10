<template>
  <div>
    <div class="itsm-table-card">
      <div class="itsm-table-header">
        <span class="itsm-table-title">{{ $t('message.itsmPage.slaPolicies') }}</span>
        <el-button size="small" type="primary" v-can="'itsm:sla:edit'" @click="onCreate">
          <el-icon><Plus /></el-icon> {{ $t('message.slaPolicy.createSlaPolicy') }}
        </el-button>
      </div>
      <el-table :data="items" v-loading="loading" stripe style="width:100%" size="small"
        :empty-text="loading ? $t('message.itsmPage.loading') : $t('message.itsmPage.noSla')">
        <el-table-column prop="name" :label="$t('message.itsmPage.colSLAPolicy')" min-width="140" />
        <el-table-column prop="priority" :label="$t('message.ticketCreate.priority')" width="80" />
        <el-table-column :label="$t('message.slaPolicy.scheduleLabel')" width="120">
          <template #default="{ row }">{{ getScheduleName(row.schedule) }}</template>
        </el-table-column>
        <el-table-column :label="$t('message.slaPolicy.responseTime')" width="130">
          <template #default="{ row }">{{ row.response_time }}{{ unitLabel(row.response_unit) }}</template>
        </el-table-column>
        <el-table-column :label="$t('message.slaPolicy.resolveTime')" width="130">
          <template #default="{ row }">{{ row.resolve_time }}{{ unitLabel(row.resolve_unit) }}</template>
        </el-table-column>
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

    <!-- Edit/Create Dialog -->
    <el-dialog v-model="showEdit" :title="form.id ? $t('message.itsmPage.editSlaPolicy') : $t('message.slaPolicy.createSlaPolicy')" width="500px" top="15vh" destroy-on-close append-to-body>
      <el-form :model="form" label-width="130px" size="small">
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
        <el-form-item :label="$t('message.slaPolicy.scheduleLabel')">
          <el-select v-model="form.schedule" style="width:100%" filterable :placeholder="$t('message.slaPolicy.scheduleLabel')">
            <el-option v-for="s in scheduleOptions" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.slaPolicy.responseTime')">
          <el-input-number v-model="form.response_time" :min="1" :max="10080" style="width:120px" />
          <el-select v-model="form.response_unit" style="width:80px;margin-left:8px">
            <el-option :label="$t('message.slaPolicy.timeUnitM')" value="m" />
            <el-option :label="$t('message.slaPolicy.timeUnitH')" value="h" />
            <el-option :label="$t('message.slaPolicy.timeUnitD')" value="d" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.slaPolicy.resolveTime')">
          <el-input-number v-model="form.resolve_time" :min="1" :max="43200" style="width:120px" />
          <el-select v-model="form.resolve_unit" style="width:80px;margin-left:8px">
            <el-option :label="$t('message.slaPolicy.timeUnitM')" value="m" />
            <el-option :label="$t('message.slaPolicy.timeUnitH')" value="h" />
            <el-option :label="$t('message.slaPolicy.timeUnitD')" value="d" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('message.slaPolicy.escalationLevels')">
          <el-select v-model="form.escalation_levels" multiple style="width:100%"
            :placeholder="$t('message.slaPolicy.escalationLevels')">
            <el-option v-for="e in escalationOptions" :key="e.id" :label="`L${e.level} ${e.name}`" :value="e.id" />
          </el-select>
        </el-form-item>
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
import { Plus } from '@element-plus/icons-vue'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { slaPolicyApi, scheduleApi, escalationApi } from '/@/api/itsm/index'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const { reportStats: updateHeroStats } = useHeroConsumer()

const loading = ref(false)
const items = ref<any[]>([])

const showEdit = ref(false)
const saving = ref(false)
const form = ref<any>({
  name: '', priority: 'P3',
  schedule: null, response_time: 60, response_unit: 'm',
  resolve_time: 480, resolve_unit: 'm',
  escalation_levels: [],
  is_active: true,
})

const scheduleOptions = ref<any[]>([])
const escalationOptions = ref<any[]>([])

function unitLabel(u: string): string {
  const m: Record<string, string> = { m: 'min', h: 'h', d: 'd' }
  return m[u] || u
}

function getScheduleName(scheduleId: number): string {
  if (!scheduleId) return '-'
  const s = scheduleOptions.value.find((o: any) => o.id === scheduleId)
  return s?.name || '-'
}

async function loadItems() {
  loading.value = true
  try {
    const res = await slaPolicyApi.list()
    items.value = res?.results || res?.data || res || []
    reportStats()
  } finally { loading.value = false }
}

async function loadOptions() {
  try {
    const [sRes, eRes] = await Promise.all([
      scheduleApi.list(),
      escalationApi.list(),
    ])
    scheduleOptions.value = (sRes as any)?.results || (sRes as any)?.data || sRes || []
    escalationOptions.value = (eRes as any)?.results || (eRes as any)?.data || eRes || []
  } catch { /* ignore */ }
}

function reportStats() {
  updateHeroStats([
    { value: items.value.length, label: '策略总数' },
    { value: items.value.filter((s: any) => s.is_active).length, label: '已启用' },
  ])
}

function onCreate() {
  form.value = {
    name: '', priority: 'P3',
    schedule: null, response_time: 60, response_unit: 'm',
    resolve_time: 480, resolve_unit: 'm',
    escalation_levels: [], is_active: true,
  }
  showEdit.value = true
}

function onEdit(row: any) {
  form.value = {
    id: row.id,
    name: row.name,
    priority: row.priority,
    schedule: row.schedule,
    response_time: row.response_time ?? 60,
    response_unit: row.response_unit ?? 'm',
    resolve_time: row.resolve_time ?? 480,
    resolve_unit: row.resolve_unit ?? 'm',
    escalation_levels: (row.escalation_levels || []).map((e: any) => e.id ?? e),
    is_active: row.is_active,
  }
  showEdit.value = true
}

async function onSave() {
  saving.value = true
  try {
    const { id, name, priority, schedule, response_time, response_unit,
      resolve_time, resolve_unit, escalation_levels, is_active } = form.value
    const payload = {
      name, priority, schedule, response_time, response_unit,
      resolve_time, resolve_unit, escalation_levels, is_active,
    }
    if (id) {
      await slaPolicyApi.update(id, payload)
    } else {
      await slaPolicyApi.create(payload)
    }
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
  loadOptions()
  if (props.active) loadItems()
})

watch(() => props.active, (isActive) => {
  if (isActive && items.value.length === 0) loadItems()
})
</script>
