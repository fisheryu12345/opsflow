<template>
  <div class="service-detail" v-loading="loading">
    <!-- Back button -->
    <div class="sd-back" @click="$emit('back')">
      <el-icon><ArrowLeft /></el-icon> {{ $t('message.serviceDetail.backToList') }}
    </div>

    <!-- Detail Card -->
    <div class="sd-card" v-if="item">
      <!-- Header -->
      <div class="sd-header">
        <div class="sd-icon">{{ item.icon || '📋' }}</div>
        <div class="sd-info">
          <div class="sd-name">{{ item.name }}</div>
          <div class="sd-meta">
            <span class="sd-category" v-if="item.category_name">{{ item.category_name }}</span>
            <el-tag :type="item.mode === 'flow' ? 'primary' : 'success'" size="small">
              {{ item.mode === 'flow' ? $t('message.serviceDetail.flowMode') : $t('message.serviceDetail.lightweightMode') }}
            </el-tag>
            <span v-if="item.expected_duration" class="sd-duration">{{ $t('message.serviceDetail.expectedDuration', { duration: item.expected_duration }) }}</span>
          </div>
        </div>
      </div>

      <!-- Description -->
      <div class="sd-section" v-if="item.description">
        <div class="sd-section-title">{{ $t('message.serviceDetail.serviceDesc') }}</div>
        <div class="sd-desc">{{ item.description }}</div>
      </div>

      <!-- Form -->
      <div class="sd-section">
        <div class="sd-section-title">{{ $t('message.serviceDetail.applyInfo') }}</div>
        <ItsmFormRenderer
          mode="fill"
          :fields="nodeFormFields"
          :data="formData"
          :submitting="submitting"
          :submit-text="$t('message.serviceDetail.submitApply')"
          :cancel-text="$t('message.common.cancel')"
          @field-change="(k, v) => formData[k] = v"
          @submit="onSubmit"
          @cancel="$emit('back')"
        />
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import ItsmFormRenderer from '/@/components/ItsmFormRenderer/index.vue'
import { serviceItemApi, SubmitServiceItem, stateApi } from '/@/api/itsm/index'

const props = defineProps<{ serviceId: number }>()
const emit = defineEmits<{ back: []; submitted: [ticketId: number] }>()
const { t } = useI18n()

const loading = ref(false)
const submitting = ref(false)
const item = ref<any>(null)
const workflowFields = ref<any[]>([])

const formData = reactive<Record<string, any>>({})

// Use workflow's first NORMAL node fields as the form
const nodeFormFields = computed(() => {
  if (workflowFields.value.length) return workflowFields.value
  // Fallback: item.form_fields if no workflow fields loaded
  return item.value?.form_fields || []
})

async function loadDetail() {
  loading.value = true
  try {
    const res = await serviceItemApi.detail(String(props.serviceId))
    item.value = (res as any).data || res
    // Load the workflow's first NORMAL node fields for the form
    if (item.value?.mode === 'flow' && item.value?.workflow) {
      await loadWorkflowFields()
    }
  } catch {
    ElMessage.error('加载服务详情失败')
  }
  loading.value = false
}

async function loadWorkflowFields() {
  try {
    const res: any = await stateApi.list({ workflow: item.value.workflow, type: 'NORMAL' })
    const states = res?.results || res?.data || res || []
    const list = Array.isArray(states) ? states : []
    const firstNormal = list.find((s: any) => s.type === 'NORMAL')
    if (firstNormal) {
      const fields = firstNormal.fields || []
      // Merge service item overrides into workflow fields
      const overrides = item.value?.form_fields || []
      const merged = [...fields]
      const existingKeys = new Set(fields.map((f: any) => f.key))
      for (const f of overrides) {
        if (!existingKeys.has(f.key)) merged.push(f)
      }
      workflowFields.value = merged
    }
  } catch {
    // Fallback: use item.form_fields
    workflowFields.value = item.value?.form_fields || []
  }
}

async function onSubmit(data?: Record<string, any>) {
  if (submitting.value) return  // Prevent double submission
  const source = data || formData
  console.log('[ServiceDetail] onSubmit source:', JSON.stringify(source))
  // Extract title from form data (workflow field) or fallback to service item name
  const title = (source.title || source['title'] || item.value?.name || '').trim()
  if (!title) {
    ElMessage.warning('请输入标题')
    return
  }
  submitting.value = true
  try {
    const { title: _title, priority, ...rest } = source
    const payload = {
      title: _title || title,
      priority: priority || 'P3',
      form_data: { title: _title || title, priority: priority || 'P3', ...rest },
    }
    console.log('[ServiceDetail] SubmitServiceItem payload:', JSON.stringify(payload))
    const res = await SubmitServiceItem(props.serviceId, payload)
    const respData = (res as any).data || res
    const ticketId = respData?.ticket_id
    if (ticketId) {
      emit('submitted', ticketId)
    } else {
      ElMessage.success('提交成功')
      emit('back')
    }
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || '提交失败')
  }
  submitting.value = false
}

onMounted(() => loadDetail())
</script>

<style lang="scss" scoped>
.service-detail {
  width: 100%;
  height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  padding: 8px 16px 24px;
}

.sd-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  overflow: hidden;
}

.sd-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #409EFF;
  cursor: pointer;
  margin-bottom: 16px;
  &:hover { text-decoration: underline; }
}

.sd-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid #f0f0f0;
}
.sd-icon { font-size: 36px; }
.sd-name { font-size: 18px; font-weight: 600; color: #303133; }
.sd-meta { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
.sd-category { font-size: 12px; color: #909399; }
.sd-duration { font-size: 12px; color: #c0c4cc; }

.sd-section { padding: 16px 20px; border-bottom: 1px solid #f5f6fa; }
.sd-section:last-of-type { border-bottom: none; }
.sd-section-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 10px; }
.sd-desc { font-size: 13px; color: #606266; line-height: 1.6; }

.sd-form { max-width: 100%; }

.sd-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
}
</style>
