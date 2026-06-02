<template>
  <el-dialog
    v-model="visible"
    title="New Template"
    width="700px"
    top="6vh"
    :close-on-click-modal="false"
    class="create-wizard"
    @close="handleClose"
  >
    <!-- Step Progress -->
    <div class="wizard-steps">
      <el-steps :active="activeStep" align-center finish-status="success" :space="260">
        <el-step title="① Basic Info" description="Name & Category" />
        <el-step title="② Method" description="Creation Method" />
      </el-steps>
    </div>

    <el-divider style="margin: 16px 0 18px" />

    <!-- ==================== Step 1: Basic Info ==================== -->
    <div v-show="activeStep === 0" class="step-content">
      <el-form label-position="top" size="default" class="info-form">
        <el-form-item label="Project" required>
          <el-select v-model="form.project_id" placeholder="Select project..." filterable>
            <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Template Name" required>
          <el-input v-model="form.name" placeholder="e.g. Database Backup Pipeline" maxlength="200" />
        </el-form-item>
        <el-form-item label="Category" required>
          <el-select v-model="form.category" placeholder="Select category..." filterable>
            <el-option v-for="cat in categories" :key="cat.code" :label="cat.name" :value="cat.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="Description (optional)">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="Briefly describe the purpose of this template" maxlength="500" />
        </el-form-item>
      </el-form>
    </div>

    <!-- ==================== Step 2: Creation Method ==================== -->
    <div v-show="activeStep === 1" class="step-content">
      <div class="method-options">
        <!-- Blank -->
        <div class="method-card" :class="{ selected: method === 'blank' }" @click="method = 'blank'">
          <div class="method-card-left">
            <div class="method-icon">📄</div>
            <div class="method-info">
              <div class="method-title">Blank Canvas</div>
              <div class="method-desc">Start from scratch — an empty pipeline with just Start & End nodes</div>
            </div>
          </div>
          <el-radio v-model="method" value="blank" size="small" />
        </div>

        <!-- AI Generate -->
        <div class="method-card" :class="{ selected: method === 'ai' }" @click="method = 'ai'">
          <div class="method-card-left">
            <div class="method-icon">🤖</div>
            <div class="method-info">
              <div class="method-title">AI Generate</div>
              <div class="method-desc">Describe your workflow in plain English — AI generates the pipeline for you</div>
            </div>
          </div>
          <el-radio v-model="method" value="ai" size="small" />
        </div>

        <!-- Clone -->
        <div class="method-card" :class="{ selected: method === 'clone' }" @click="method = 'clone'">
          <div class="method-card-left">
            <div class="method-icon">📋</div>
            <div class="method-info">
              <div class="method-title">Clone from Existing</div>
              <div class="method-desc">Duplicate an existing template as a starting point</div>
            </div>
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
          placeholder='e.g. "Inspect disk space on all hosts at 2 AM daily, then send an alert if usage exceeds 90%"'
        />
      </div>

      <!-- Clone Selector -->
      <div v-if="method === 'clone'" class="method-extra">
        <el-select
          v-model="cloneTemplateId"
          placeholder="Select a template to clone..."
          filterable
          style="width:100%"
        >
          <el-option-group v-if="projectTemplates.length" label="📁 Project Templates">
            <el-option v-for="t in projectTemplates" :key="t.id" :label="t.name" :value="t.id" />
          </el-option-group>
          <el-option-group v-if="publicTemplates.length" label="🌐 Public Templates">
            <el-option v-for="t in publicTemplates" :key="t.id" :value="t.id">
              <span>{{ t.name }}</span>
              <el-tag size="small" type="warning" style="margin-left:6px">public</el-tag>
            </el-option>
          </el-option-group>
        </el-select>
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
            class="btn-create"
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
import { ElMessage } from 'element-plus'
import { CircleCheck } from '@element-plus/icons-vue'
import { CreateTemplate, CreateFromAi, ExportTemplate, ImportTemplate, GetTemplates, UpdateTemplate } from '/@/api/opsflow/templates'
import { GetTemplateCategories } from '/@/api/opsflow/template-categories'
import { useOpsflowStore } from '../stores/opsflowStore'

const store = useOpsflowStore()

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

const form = ref({ name: '', category: '', description: '', project_id: null as number | null })
const projectList = computed(() => store.myProjects)

const method = ref<'blank' | 'ai' | 'clone'>('blank')
const aiPrompt = ref('')
const cloneTemplateId = ref<number | null>(null)

const projectTemplates = computed(() => (allTemplates.value || []).filter((t: any) => !t.is_public))
const publicTemplates = computed(() => (allTemplates.value || []).filter((t: any) => t.is_public))

const canNext = computed(() =>
  form.value.project_id && form.value.name.trim() && form.value.category,
)

const canSubmit = computed(() => {
  if (!form.value.project_id || !form.value.name.trim() || !form.value.category) return false
  if (method.value === 'ai' && !aiPrompt.value.trim()) return false
  if (method.value === 'clone' && !cloneTemplateId.value) return false
  return true
})

function nextStep() { activeStep.value = Math.min(activeStep.value + 1, 1) }
function prevStep() { activeStep.value = Math.max(activeStep.value - 1, 0) }
function handleClose() { emit('update:modelValue', false) }

const extractData = (res: any): any => {
  if (res?.code === 2000 && res?.data) return res.data
  return res?.id ? res : res
}

async function handleCreate() {
  submitting.value = true
  if (form.value.project_id) {
    store.setCurrentProjectId(form.value.project_id)
  }
  try {
    let template: any

    if (method.value === 'ai') {
      const res = await CreateFromAi({ input: aiPrompt.value })
      template = extractData(res)
      // CreateFromAi 返回 {template: {...}, validation: {...}}，需解一层
      if (template?.template?.id) template = template.template
      if (template?.id) {
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
      const importRes = await ImportTemplate({ data: exportData })
      template = extractData(importRes)
    } else {
      const res = await CreateTemplate({
        name: form.value.name,
        category: form.value.category,
        description: form.value.description,
      })
      template = extractData(res)
    }

    if (!template?.id) throw new Error('Template creation returned no ID')

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

watch(() => props.modelValue, async (val) => {
  if (!val) return
  activeStep.value = 0
  const defaultProject = store.currentProjectId || store.myProjects[0]?.id || null
  form.value = { name: '', category: '', description: '', project_id: defaultProject }
  method.value = 'blank'
  aiPrompt.value = ''
  cloneTemplateId.value = null

  try {
    const [catRes, tplRes] = await Promise.all([
      GetTemplateCategories(),
      GetTemplates({ limit: 200 }),
    ])
    categories.value = catRes.data?.data || catRes.data || []
    allTemplates.value = tplRes.data?.results || tplRes.data || tplRes.results || []
  } catch {
    categories.value = []
    allTemplates.value = []
  }
})
</script>

<style scoped>
.create-wizard :deep(.el-dialog__body) {
  padding: 0 28px;
  min-height: 340px;
}

/* Steps */
.wizard-steps {
  padding: 18px 0 0;
}
.wizard-steps :deep(.el-step__title) {
  font-size: 13px;
  font-weight: 500;
}
.wizard-steps :deep(.el-step__description) {
  font-size: 11px;
  color: #909399;
}

/* Body */
.step-content {
  min-height: 280px;
  padding-bottom: 8px;
}

/* ===== Step 1: Form ===== */
.info-form {
  max-width: 500px;
}
.info-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 4px;
}
.info-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

/* ===== Step 2: Method Cards ===== */
.method-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.method-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border: 1.5px solid #ebeef5;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
}
.method-card:hover {
  border-color: #409EFF;
  background: #fafcff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.08);
}
.method-card.selected {
  border-color: #409EFF;
  background: linear-gradient(135deg, #ecf5ff, #f0f8ff);
  box-shadow: 0 2px 12px rgba(64,158,255,0.12);
}
.method-card-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
}
.method-icon {
  font-size: 26px;
  flex-shrink: 0;
  width: 36px;
  text-align: center;
}
.method-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}
.method-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
.method-extra {
  margin-top: 6px;
}

/* Footer */
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
.btn-create {
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-color: transparent;
}
.btn-create:hover {
  background: linear-gradient(135deg, #5a6fd6, #6a4199);
  border-color: transparent;
}
</style>
