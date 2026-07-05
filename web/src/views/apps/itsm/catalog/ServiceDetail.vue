<template>
  <div class="service-detail" v-loading="loading">
    <!-- Back button -->
    <div class="sd-back" @click="$emit('back')">
      <el-icon><ArrowLeft /></el-icon> 返回服务列表
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
              {{ item.mode === 'flow' ? '流程驱动' : '快捷服务' }}
            </el-tag>
            <span v-if="item.expected_duration" class="sd-duration">⏱ 预计 {{ item.expected_duration }}</span>
          </div>
        </div>
      </div>

      <!-- Description -->
      <div class="sd-section" v-if="item.description">
        <div class="sd-section-title">服务说明</div>
        <div class="sd-desc">{{ item.description }}</div>
      </div>

      <!-- Form -->
      <div class="sd-section">
        <div class="sd-section-title">申请信息</div>
        <el-form label-position="top" size="small" class="sd-form">
          <el-form-item label="申请标题" required>
            <el-input v-model="form.title" placeholder="请输入申请标题" :maxlength="200" />
          </el-form-item>
          <el-form-item label="优先级">
            <el-select v-model="form.priority" style="width:100%">
              <el-option label="P1 危急" value="P1" />
              <el-option label="P2 高" value="P2" />
              <el-option label="P3 中" value="P3" />
              <el-option label="P4 低" value="P4" />
            </el-select>
          </el-form-item>

          <!-- Dynamic fields from service item form_fields -->
          <template v-for="(field, idx) in item.form_fields || []" :key="idx">
            <el-form-item :label="field.name" :required="field.required">
              <template v-if="field.type === 'TEXT'">
                <el-input v-model="formData[field.key]" type="textarea" :rows="3" :placeholder="field.placeholder" />
              </template>
              <template v-else-if="field.type === 'SELECT'">
                <el-select v-model="formData[field.key]" style="width:100%" :placeholder="field.placeholder">
                  <el-option v-for="c in (field.choice || [])" :key="c.value" :label="c.label" :value="c.value" />
                </el-select>
              </template>
              <template v-else-if="field.type === 'RADIO'">
                <el-radio-group v-model="formData[field.key]">
                  <el-radio v-for="c in (field.choice || [])" :key="c.value" :value="c.value">{{ c.label }}</el-radio>
                </el-radio-group>
              </template>
              <template v-else-if="field.type === 'CHECKBOX'">
                <el-checkbox-group v-model="formData[field.key]">
                  <el-checkbox v-for="c in (field.choice || [])" :key="c.value" :label="c.value">{{ c.label }}</el-checkbox>
                </el-checkbox-group>
              </template>
              <template v-else>
                <el-input v-model="formData[field.key]" :placeholder="field.placeholder" />
              </template>
            </el-form-item>
          </template>
        </el-form>
      </div>

      <!-- Submit -->
      <div class="sd-actions">
        <el-button @click="$emit('back')">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">
          <el-icon><Select /></el-icon> 提交申请
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Select } from '@element-plus/icons-vue'
import { serviceItemApi, SubmitServiceItem } from '/@/api/itsm/index'

const props = defineProps<{ serviceId: number }>()
const emit = defineEmits<{ back: []; submitted: [ticketId: number] }>()

const loading = ref(false)
const submitting = ref(false)
const item = ref<any>(null)

const form = reactive({ title: '', priority: 'P3' })
const formData = reactive<Record<string, any>>({})

async function loadDetail() {
  loading.value = true
  try {
    const res = await serviceItemApi.detail(String(props.serviceId))
    item.value = (res as any).data || res
  } catch {
    ElMessage.error('加载服务详情失败')
  }
  loading.value = false
}

async function onSubmit() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入申请标题')
    return
  }
  submitting.value = true
  try {
    const res = await SubmitServiceItem(props.serviceId, {
      title: form.title,
      priority: form.priority,
      form_data: { ...formData },
    })
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
  max-width: 100%;
  margin: 0 auto;
  padding: 8px 0 24px;
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

.sd-card {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  overflow: hidden;
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
