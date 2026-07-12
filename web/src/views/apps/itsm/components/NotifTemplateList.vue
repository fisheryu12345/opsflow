<template>
  <div>
    <div class="itsm-table-card">
      <div class="itsm-table-header">
        <span class="itsm-table-title">{{ $t('message.notifTemplate.title') }}</span>
        <el-button size="small" type="primary" v-can="'itsm:notif_template:edit'" @click="onCreate">
          <el-icon><Plus /></el-icon> {{ $t('message.notifTemplate.create') }}
        </el-button>
      </div>
      <el-table :data="items" v-loading="loading" stripe style="width:100%" size="small"
        :empty-text="loading ? $t('message.itsmPage.loading') : $t('message.common.empty')">
        <el-table-column prop="name" :label="$t('message.notifTemplate.colName')" min-width="140" />
        <el-table-column :label="$t('message.notifTemplate.colChannels')" width="160">
          <template #default="{ row }">
            <el-tag v-for="ch in (row.channels || [])" :key="ch" size="small" style="margin-right:4px">
              {{ ch === 'site' ? $t('message.notifTemplate.channelSite') : ch === 'wecom' ? $t('message.notifTemplate.channelWecom') : ch === 'dingtalk' ? $t('message.notifTemplate.channelDingtalk') : $t('message.notifTemplate.channelEmail') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.notifTemplate.colReceivers')" width="120">
          <template #default="{ row }">
            <el-tag v-for="r in (row.receivers || [])" :key="r" size="small" style="margin-right:4px">
              {{ r === 'processor' ? $t('message.notifTemplate.receiverProcessor') : r === 'starter' ? $t('message.notifTemplate.receiverStarter') : $t('message.notifTemplate.receiverLeader') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colEnabled')" width="70" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" size="small" @change="(v: boolean) => onToggle(row, v)" />
          </template>
        </el-table-column>
        <el-table-column :label="$t('message.itsmPage.colActions')" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="onEdit(row)">{{ $t('message.common.edit') }}</el-button>
            <el-button link type="danger" size="small" @click="onDelete(row)">{{ $t('message.common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog v-model="showEdit" :title="form.id ? $t('message.notifTemplate.edit') : $t('message.notifTemplate.create')"
      width="600px" top="10vh" destroy-on-close append-to-body>
      <el-form :model="form" label-width="100px" size="small">
        <el-form-item :label="$t('message.notifTemplate.colName')" required>
          <el-input v-model="form.name" :placeholder="$t('message.notifTemplate.colName')" />
        </el-form-item>
        <el-form-item :label="$t('message.notifTemplate.colName') + '(EN)'">
          <el-input v-model="form.name_en" placeholder="English name" />
        </el-form-item>
        <el-form-item :label="$t('message.itsmPage.colEnabled')">
          <el-switch v-model="form.is_active" />
        </el-form-item>

        <el-divider content-position="left">{{ $t('message.notifTemplate.titleTpl') }}</el-divider>
        <el-form-item :label="$t('message.notifTemplate.titleTpl')">
          <el-input v-model="form.title_tpl" :placeholder="$t('message.notifTemplate.titleTpl')" />
        </el-form-item>
        <el-form-item :label="$t('message.notifTemplate.bodyTpl')">
          <el-input v-model="form.body_tpl" type="textarea" :rows="4" :placeholder="$t('message.notifTemplate.bodyTpl')" />
        </el-form-item>

        <el-divider content-position="left">{{ $t('message.notifTemplate.channels') }} &amp; {{ $t('message.notifTemplate.receivers') }}</el-divider>
        <el-form-item :label="$t('message.notifTemplate.channels')">
          <el-checkbox-group v-model="form.channels">
            <el-checkbox value="site">{{ $t('message.notifTemplate.channelSite') }}</el-checkbox>
            <el-checkbox value="wecom">{{ $t('message.notifTemplate.channelWecom') }}</el-checkbox>
            <el-checkbox value="dingtalk">{{ $t('message.notifTemplate.channelDingtalk') }}</el-checkbox>
            <el-checkbox value="email">{{ $t('message.notifTemplate.channelEmail') }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item :label="$t('message.notifTemplate.receivers')">
          <el-checkbox-group v-model="form.receivers">
            <el-checkbox value="processor">{{ $t('message.notifTemplate.receiverProcessor') }}</el-checkbox>
            <el-checkbox value="starter">{{ $t('message.notifTemplate.receiverStarter') }}</el-checkbox>
            <el-checkbox value="leader">{{ $t('message.notifTemplate.receiverLeader') }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <div class="template-hint">{{ $t('message.notifTemplate.templateHints') }}</div>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import { notificationTemplateApi } from '/@/api/itsm/index'
import { useHeroConsumer } from '/@/composables/useHeroConsumer'

const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const { reportStats: updateHeroStats } = useHeroConsumer()

const loading = ref(false)
const items = ref<any[]>([])
const showEdit = ref(false)
const saving = ref(false)
const form = ref<any>({
  id: null, name: '', name_en: '', is_active: true,
  channels: ['site'], title_tpl: '', body_tpl: '',
  receivers: ['processor'],
})

async function loadItems() {
  loading.value = true
  try {
    const res = await notificationTemplateApi.list() as any
    items.value = res?.results || res?.data || res || []
  } catch { items.value = [] }
  finally { loading.value = false }
}

function onCreate() {
  form.value = { id: null, name: '', name_en: '', is_active: true, channels: ['site'], title_tpl: '', body_tpl: '', receivers: ['processor'] }
  showEdit.value = true
}

function onEdit(row: any) {
  form.value = {
    id: row.id,
    name: row.name_en || row.name,
    name_en: row.name_en || '',
    is_active: row.is_active,
    channels: row.channels || ['site'],
    title_tpl: row.title_tpl || '',
    body_tpl: row.body_tpl || '',
    receivers: row.receivers || ['processor'],
  }
  showEdit.value = true
}

async function onSave() {
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      name_en: form.value.name_en,
      is_active: form.value.is_active,
      channels: form.value.channels,
      title_tpl: form.value.title_tpl,
      body_tpl: form.value.body_tpl,
      receivers: form.value.receivers,
    }
    if (form.value.id) {
      await notificationTemplateApi.update(form.value.id, payload)
      ElMessage.success('模板已更新')
    } else {
      await notificationTemplateApi.create(payload)
      ElMessage.success('模板已创建')
    }
    showEdit.value = false
    await loadItems()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally { saving.value = false }
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm('确定删除此模板？', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  try {
    await notificationTemplateApi.delete(row.id)
    ElMessage.success('已删除')
    await loadItems()
  } catch { ElMessage.error('删除失败') }
}

async function onToggle(row: any, v: boolean) {
  try {
    await notificationTemplateApi.update(row.id, { is_active: v })
    row.is_active = v
  } catch { row.is_active = !v; ElMessage.error('操作失败') }
}

function reportStats() {
  updateHeroStats([
    { value: items.value.length, label: '模板总数' },
    { value: items.value.filter((t: any) => t.is_active).length, label: '已启用' },
  ])
}

onMounted(() => { if (props.active) loadItems().then(reportStats) })
watch(() => props.active, (v) => { if (v) loadItems().then(reportStats) })
</script>

<style lang="scss" scoped>
.template-hint { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px; }
</style>
