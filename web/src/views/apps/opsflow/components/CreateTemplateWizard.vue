<template>
  <el-dialog
    v-model="visible"
    title="New Template Wizard"
    width="680px"
    top="8vh"
    :close-on-click-modal="false"
    class="wizard-dialog"
    @close="handleClose"
  >
    <!-- Step Progress -->
    <div class="wizard-steps">
      <el-steps :active="activeStep" align-center finish-status="success" :space="240">
        <el-step title="① 基本信息" description="Name & Category" />
        <el-step title="② 创建方式" description="Creation Method" />
      </el-steps>
    </div>

    <el-divider style="margin: 16px 0 20px" />

    <div class="wizard-body">
      <!-- ==================== Step 1: Basic Info ==================== -->
      <div v-show="activeStep === 0" class="step-content">
        <div class="step-header">
          <div class="step-icon">📋</div>
          <div>
            <h3 class="step-title">基本信息</h3>
            <p class="step-desc">设置模板名称、分类和描述</p>
          </div>
        </div>

        <el-form label-width="80px" size="default" class="info-form">
          <el-form-item label="名称" required>
            <el-input v-model="form.name" placeholder="输入模板名称" maxlength="200" />
          </el-form-item>
          <el-form-item label="分类" required>
            <el-select v-model="form.category" placeholder="选择分类" filterable style="width:100%">
              <el-option v-for="cat in categories" :key="cat.code" :label="cat.name" :value="cat.code" />
            </el-select>
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选的模板描述" maxlength="500" />
          </el-form-item>
        </el-form>
      </div>

      <!-- ==================== Step 2: Creation Method ==================== -->
      <div v-show="activeStep === 1" class="step-content">
        <div class="step-header">
          <div class="step-icon">🚀</div>
          <div>
            <h3 class="step-title">选择创建方式</h3>
            <p class="step-desc">选择如何创建此模板</p>
          </div>
        </div>

        <div class="method-options">
          <!-- Blank -->
          <div class="method-card" :class="{ selected: method === 'blank' }" @click="method = 'blank'">
            <div class="method-icon">📄</div>
            <div class="method-info">
              <div class="method-title">空白创建</div>
              <div class="method-desc">创建空模板，从零开始设计流程</div>
            </div>
            <el-radio v-model="method" value="blank" size="small" />
          </div>

          <!-- AI Generate -->
          <div class="method-card" :class="{ selected: method === 'ai' }" @click="method = 'ai'">
            <div class="method-icon">🤖</div>
            <div class="method-info">
              <div class="method-title">AI 生成</div>
              <div class="method-desc">用自然语言描述，自动生成流程</div>
            </div>
            <el-radio v-model="method" value="ai" size="small" />
          </div>

          <!-- Clone -->
          <div class="method-card" :class="{ selected: method === 'clone' }" @click="method = 'clone'">
            <div class="method-icon">📋</div>
            <div class="method-info">
              <div class="method-title">从已有模板克隆</div>
              <div class="method-desc">基于已有模板创建副本</div>
            </div>
            <el-radio v-model="method" value="clone" size="small" />
          </div>
        </div>

        <!-- AI Input -->
        <div v-if="method === 'ai'" class="method-extra">
          <el-input
            v-model="aiPrompt"
            type="textarea"
            :rows="4"
            placeholder="描述你想要的流程，例如：每天凌晨2点备份数据库，然后发送通知到企业微信"
          />
        </div>

        <!-- Clone Selector -->
        <div v-if="method === 'clone'" class="method-extra">
          <el-select
            v-model="cloneTemplateId"
            placeholder="选择要克隆的模板..."
            filterable
            style="width:100%"
            size="default"
          >
            <el-option-group v-if="projectTemplates.length" label="📁 项目模板">
              <el-option v-for="t in projectTemplates" :key="t.id" :label="t.name" :value="t.id" />
            </el-option-group>
            <el-option-group v-if="publicTemplates.length" label="🌐 公共模板">
              <el-option v-for="t in publicTemplates" :key="t.id" :value="t.id">
                <span>{{ t.name }}</span>
                <el-tag size="small" type="warning" style="margin-left:6px">公共</el-tag>
              </el-option>
            </el-option-group>
          </el-select>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <div class="wizard-footer">
        <div class="footer-left">
          <el-button v-if="activeStep > 0" text size="default" @click="prevStep">← Back</el-button>
        </div>
        <div class="footer-right">
          <el-button plain size="default" @click="visible = false">Cancel</el-button>
          <el-button
            v-if="activeStep < 1"
            type="primary"
            size="default"
            :disabled="!canNext"
            @click="nextStep"
          >
            Continue →
          </el-button>
          <el-button
            v-else
            type="primary"
            size="default"
            :loading="submitting"
            :disabled="!canSubmit"
            @click="handleCreate"
          >
            <el-icon><CircleCheck /></el-icon> Create
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

/** 从 API 响应中提取数据对象（兼容多种响应格式） */
function extractData(res: any): any {
  console.log('[extractData] input type:', typeof res, 'has id:', !!res?.id)
  // service.ts 拦截器返回的是 response.data = {code:2000, data:{...}, msg:"..."}
  if (res?.code === 2000 && res?.data) return res.data
  // 如果直接是 axios 响应
  if (res?.data?.code === 2000 && res?.data?.data) return res.data.data
  // flat response
  if (res?.id) return res
  return res
}
import { ElMessage } from 'element-plus'
import { CircleCheck } from '@element-plus/icons-vue'
import { CreateTemplate, CreateFromAi, GetTemplateDetail, ExportTemplate } from '/@/api/opsflow/templates'
import { GetTemplates } from '/@/api/opsflow/templates'
import { GetTemplateCategories } from '/@/api/opsflow/template-categories'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'created': [template: any]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const activeStep = ref(0)
const submitting = ref(false)
const categories = ref<any[]>([])
const allTemplates = ref<any[]>([])

// Step 1 form
const form = ref({ name: '', category: '', description: '' })

// Step 2 method
const method = ref<'blank' | 'ai' | 'clone'>('blank')
const aiPrompt = ref('')
const cloneTemplateId = ref<number | null>(null)

const projectTemplates = computed(() => (allTemplates.value || []).filter((t: any) => !t.is_public))
const publicTemplates = computed(() => (allTemplates.value || []).filter((t: any) => t.is_public))

// Navigation guards
const canNext = computed(() => {
  return form.value.name.trim() && form.value.category
})

const canSubmit = computed(() => {
  if (!form.value.name.trim() || !form.value.category) return false
  if (method.value === 'ai' && !aiPrompt.value.trim()) return false
  if (method.value === 'clone' && !cloneTemplateId.value) return false
  return true
})

function nextStep() {
  if (activeStep.value < 1) {
    activeStep.value++
  }
}

function prevStep() {
  if (activeStep.value > 0) {
    activeStep.value--
  }
}

async function handleCreate() {
  submitting.value = true
  try {
    let template: any

    if (method.value === 'ai') {
      const res = await CreateFromAi({ input: aiPrompt.value })
      template = extractData(res)
      if (template?.id) {
        const { UpdateTemplate } = await import('/@/api/opsflow/templates')
        await UpdateTemplate(template.id, {
          name: form.value.name,
          category: form.value.category,
          description: form.value.description,
        })
        template.name = form.value.name
        template.category = form.value.category
        template.description = form.value.description
      }
    } else if (method.value === 'clone') {
      const exportRes = await ExportTemplate(cloneTemplateId.value!)
      const exportData = extractData(exportRes)
      if (exportData?.template) {
        exportData.template.name = form.value.name
        exportData.template.category = form.value.category
        exportData.template.description = form.value.description
      }
      const { ImportTemplate } = await import('/@/api/opsflow/templates')
      const importRes = await ImportTemplate({ data: exportData })
      template = extractData(importRes)
    } else {
      const res = await CreateTemplate({
        name: form.value.name,
        category: form.value.category,
        description: form.value.description,
      })
      console.log('[CreateWizard] raw CreateTemplate response:', JSON.stringify(res).slice(0, 500))
      template = extractData(res)
      console.log('[CreateWizard] extractData result:', JSON.stringify(template).slice(0, 300))
    }

    if (!template?.id) {
      console.error('[CreateWizard] CreateTemplate failed: no id in response', JSON.stringify(template))
      throw new Error('Template creation returned no ID')
    }

    ElMessage.success(`Template "${template.name}" created`)
    visible.value = false
    emit('created', template)
  } catch (e: any) {
    const errMsg = e?.response?.data?.msg || e?.msg || e?.message || 'Creation failed'
    ElMessage.error(errMsg)
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  emit('update:modelValue', false)
}

// Load data on open
watch(() => props.modelValue, async (val) => {
  if (!val) return
  activeStep.value = 0
  form.value = { name: '', category: '', description: '' }
  method.value = 'blank'
  aiPrompt.value = ''
  cloneTemplateId.value = null

  try {
    const catRes = await GetTemplateCategories()
    categories.value = catRes.data?.data || catRes.data || []
  } catch {
    categories.value = []
  }

  try {
    const tplRes = await GetTemplates({ limit: 200 })
    allTemplates.value = tplRes.data?.results || tplRes.data || tplRes.results || []
  } catch {
    allTemplates.value = []
  }
})
</script>

<style scoped>
.wizard-dialog :deep(.el-dialog__body) {
  padding: 0 24px;
  min-height: 360px;
}

.wizard-steps {
  padding: 20px 0 0;
}
.wizard-steps :deep(.el-step__title) {
  font-size: 13px;
}
.wizard-steps :deep(.el-step__description) {
  font-size: 11px;
}

.wizard-body {
  min-height: 280px;
}

.step-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}
.step-icon {
  font-size: 28px;
  flex-shrink: 0;
}
.step-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}
.step-desc {
  margin: 2px 0 0;
  font-size: 12px;
  color: #909399;
}

.info-form {
  max-width: 480px;
}

.method-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.method-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.method-card:hover {
  border-color: #409EFF;
  background: #fafcff;
}
.method-card.selected {
  border-color: #409EFF;
  background: #ecf5ff;
}
.method-icon {
  font-size: 24px;
  flex-shrink: 0;
}
.method-info {
  flex: 1;
}
.method-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.method-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.method-extra {
  margin-top: 8px;
}

.wizard-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.footer-left, .footer-right {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
