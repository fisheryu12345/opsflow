<template>
  <div>
    <div class="itsm-table-card">
      <div class="itsm-table-header">
        <span class="itsm-table-title">{{ $t('message.slaSchedule.title') }}</span>
        <el-button size="small" type="primary" v-can="'itsm:sla:edit'" @click="onCreate">
          <el-icon><Plus /></el-icon> {{ $t('message.slaSchedule.newSchedule') }}
        </el-button>
      </div>
      <el-table :data="items" v-loading="loading" stripe style="width:100%" size="small"
        :empty-text="loading ? $t('message.itsmPage.loading') : $t('message.slaSchedule.noDays')">
        <el-table-column prop="name" :label="$t('message.slaSchedule.colName')" min-width="140" />
        <el-table-column :label="$t('message.slaSchedule.colProject')" width="120">
          <template #default="{ row }">
            {{ row.project_name || $t('message.slaSchedule.globalProject') }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.slaSchedule.colWorkingDays')" width="100" align="center">
          <template #default="{ row }">{{ row.days?.length || 0 }}</template>
        </el-table-column>
        <el-table-column :label="$t('message.slaSchedule.colOvertimeDays')" width="100" align="center">
          <template #default="{ row }">{{ row.workdays?.length || 0 }}</template>
        </el-table-column>
        <el-table-column :label="$t('message.slaSchedule.colHolidays')" width="100" align="center">
          <template #default="{ row }">{{ row.holidays?.length || 0 }}</template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colEnabled')" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_builtin" size="small" type="info">{{ $t('message.slaSchedule.builtinBadge') }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colActions')" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text v-can="'itsm:sla:edit'" @click="onEdit(row)">{{ $t('message.common.edit') }}</el-button>
            <el-button v-if="!row.is_builtin" size="small" text type="danger" v-can="'itsm:sla:edit'"
              @click="onDelete(row)">{{ $t('message.common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Edit Dialog -->
    <ScheduleEdit v-model="showEdit" :schedule="editTarget" @saved="onSaved" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'
import { scheduleApi } from '/@/api/itsm/index'
import ScheduleEdit from './ScheduleEdit.vue'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const { reportStats: updateHeroStats } = useHeroConsumer()
const { t } = useI18n()

const loading = ref(false)
const items = ref<any[]>([])

const showEdit = ref(false)
const editTarget = ref<any>(null)

async function loadItems() {
  loading.value = true
  try { const res = await scheduleApi.list(); items.value = res?.results || res?.data || res || []; reportStats() } finally { loading.value = false }
}

function reportStats() {
  updateHeroStats([
    { value: items.value.length, label: '排班总数' },
    { value: items.value.filter((s: any) => s.is_builtin).length, label: '内置排班' },
  ])
}

function onCreate() {
  editTarget.value = null
  showEdit.value = true
}

function onEdit(row: any) {
  editTarget.value = row
  showEdit.value = true
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(
      t('message.slaSchedule.deleteConfirm', { name: row.name }),
      t('message.common.delete').toString(),
      { type: 'warning' as const }
    )
    await scheduleApi.delete(row.id)
    ElMessage.success(t('message.common.deleted'))
    await loadItems()
  } catch { /* cancelled */ }
}

function onSaved() {
  showEdit.value = false
  loadItems()
}

onMounted(() => {
  if (props.active) loadItems()
})

watch(() => props.active, (isActive) => {
  if (isActive && items.value.length === 0) loadItems()
})
</script>
