<template>
  <el-dialog
    v-model="visible"
    :title="$t('message.template.newTemplate')"
    width="700px"
    top="6vh"
    :close-on-click-modal="false"
    class="opsflow-dialog create-wizard"
    @close="handleClose"
  >
    <!-- Step Progress -->
    <div class="wiz-header">
      <div class="wiz-steps">
        <div
          v-for="(step, i) in steps"
          :key="i"
          class="wiz-step"
          :class="{ active: activeStep === i, done: activeStep > i }"
        >
          <div class="wiz-step-indicator">
            <span v-if="activeStep > i" class="wiz-step-check">✓</span>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <div class="wiz-step-label">
            <div class="wiz-step-title">{{ step.title }}</div>
            <div class="wiz-step-desc">{{ step.desc }}</div>
          </div>
          <div v-if="i < steps.length - 1" class="wiz-step-connector" :class="{ done: activeStep > i }" />
        </div>
      </div>
      <div class="wiz-progress">
        <div class="wiz-progress-bar" :style="{ width: `${((activeStep + 1) / steps.length) * 100}%` }" />
      </div>
    </div>

    <div class="wiz-body">
      <!-- ==================== Step 1: Basic Info ==================== -->
      <div v-show="activeStep === 0" class="wiz-step-panel">
        <div class="panel-hero">
          <div class="panel-hero-icon">📝</div>
          <div class="panel-hero-text">
            <h3>{{ $t("message.template.basicInfo") }}</h3>
            <p>{{ $t("message.template.basicInfoDesc") }}</p>
          </div>
        </div>

        <div class="form-card">
          <el-form label-position="top" size="default">
            <el-form-item :label="$t('message.template.projectLabel')" required>
              <el-select v-model="form.project_id" :placeholder="$t('message.template.selectProject')" filterable>
                <el-option v-for="p in projectList" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('message.template.templateName')" required>
              <el-input v-model="form.name" :placeholder="$t('message.template.namePlaceholder')" maxlength="200" />
            </el-form-item>
            <el-form-item :label="$t('message.template.categoryLabel')" required>
              <el-select v-model="form.category" :placeholder="$t('message.template.selectCategory')" filterable>
                <el-option v-for="cat in categories" :key="cat.code" :label="cat.name" :value="cat.code" />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('message.template.descLabel')">
              <el-input v-model="form.description" type="textarea" :rows="2" :placeholder="$t('message.template.descPlaceholder')" maxlength="500" />
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- ==================== Step 2: Creation Method ==================== -->
      <div v-show="activeStep === 1" class="wiz-step-panel">
        <div class="panel-hero">
          <div class="panel-hero-icon">🎯</div>
          <div class="panel-hero-text">
            <h3>{{ $t("message.template.creationMethod") }}</h3>
            <p>{{ $t("message.template.creationMethodDesc") }}</p>
          </div>
        </div>

        <div class="mode-selector">
          <div class="mode-card" :class="{ active: method === 'blank' }" @click="method = 'blank'">
            <div class="mode-card-icon">📄</div>
            <div class="mode-card-content">
              <div class="mode-card-title">{{ $t("message.template.blankCanvas") }}</div>
              <div class="mode-card-desc">{{ $t("message.template.blankCanvasDesc") }}</div>
            </div>
            <div class="mode-card-radio" :class="{ checked: method === 'blank' }" />
          </div>

          <div class="mode-card" :class="{ active: method === 'ai' }" @click="method = 'ai'">
            <div class="mode-card-icon">🤖</div>
            <div class="mode-card-content">
              <div class="mode-card-title">{{ $t("message.template.aiGenerate") }}</div>
              <div class="mode-card-desc">{{ $t("message.template.aiGenerateDesc") }}</div>
            </div>
            <div class="mode-card-radio" :class="{ checked: method === 'ai' }" />
          </div>

          <div class="mode-card" :class="{ active: method === 'clone' }" @click="method = 'clone'">
            <div class="mode-card-icon">📋</div>
            <div class="mode-card-content">
              <div class="mode-card-title">{{ $t("message.template.cloneExisting") }}</div>
              <div class="mode-card-desc">{{ $t("message.template.cloneExistingDesc") }}</div>
            </div>
            <div class="mode-card-radio" :class="{ checked: method === 'clone' }" />
          </div>

          <div class="mode-card" :class="{ active: method === 'dr' }" @click="method = 'dr'">
            <div class="mode-card-icon">🔄</div>
            <div class="mode-card-content">
              <div class="mode-card-title">{{ $t("message.template.drSwitch") }}</div>
              <div class="mode-card-desc">{{ $t("message.template.drSwitchDesc") }}</div>
            </div>
            <div class="mode-card-radio" :class="{ checked: method === 'dr' }" />
          </div>
        </div>

        <transition name="panel-fade">
          <div v-if="method === 'ai'" class="extra-card">
            <div class="extra-card-header">
              <el-icon size="15" color="#409EFF"><ChatDotSquare /></el-icon>
              <span>{{ $t("message.template.describePipeline") }}</span>
            </div>
            <el-input
              v-model="aiPrompt"
              type="textarea"
              :rows="4"
              :placeholder="$t('message.template.aiPlaceholder')"
            />
          </div>

          <div v-else-if="method === 'clone'" class="extra-card">
            <div class="extra-card-header">
              <el-icon size="15" color="#409EFF"><CopyDocument /></el-icon>
              <span>{{ $t("message.template.selectSource") }}</span>
            </div>
            <el-select
              v-model="cloneTemplateId"
              :placeholder="$t('message.template.selectClone')"
              filterable
              style="width:100%"
              size="default"
            >
              <el-option-group v-if="projectTemplates.length" :label="'📁 ' + $t('message.template.projectTemplates')">
                <el-option v-for="t in projectTemplates" :key="t.id" :label="t.name" :value="t.id" />
              </el-option-group>
              <el-option-group v-if="publicTemplates.length" :label="'🌐 ' + $t('message.template.publicTemplates')">
                <el-option v-for="t in publicTemplates" :key="t.id" :value="t.id">
                  <span>{{ t.name }}</span>
                  <el-tag size="small" type="warning" style="margin-left:6px">{{ $t("message.template.publicTemplates") }}</el-tag>
                </el-option>
              </el-option-group>
            </el-select>
          </div>

          <div v-else-if="method === 'dr'" class="extra-card">
            <div class="extra-card-header">
              <el-icon size="15" color="#E6A23C"><Warning /></el-icon>
              <span>{{ $t("message.template.drSelectGroup") }}</span>
            </div>
            <el-select
              v-model="drGroupId"
              :placeholder="$t('message.template.drSelectGroup')"
              filterable
              style="width:100%"
              size="default"
              :loading="loadingDrGroups"
              @change="onDrGroupChange"
            >
              <el-option v-for="g in drGroups" :key="g.instance_id" :label="g.name" :value="g.instance_id">
                <span>{{ g.name }}</span>
                <el-tag v-if="g.status" size="small" :type="g.status === 'active' ? 'success' : 'warning'" style="margin-left:6px">{{ g.status }}</el-tag>
              </el-option>
            </el-select>

            <!-- 拓扑预览 -->
            <div v-if="drTopology" class="topo-preview">
              <div class="topo-preview-title">拓扑预览</div>
              <div class="topo-preview-grid">
                <div class="topo-preview-col">
                  <div class="topo-preview-subtitle">主站进程</div>
                  <div v-for="p in drTopology.primary" :key="p.id" class="topo-preview-node">
                    <span class="topo-node-dot primary" />
                    <span class="topo-node-name">{{ p.name }}</span>
                    <span class="topo-node-host">{{ p.host }}</span>
                  </div>
                  <div v-if="!drTopology.primary.length" class="topo-preview-empty">无</div>
                </div>
                <div class="topo-preview-col">
                  <div class="topo-preview-subtitle">备站进程</div>
                  <div v-for="p in drTopology.standby" :key="p.id" class="topo-preview-node">
                    <span class="topo-node-dot standby" />
                    <span class="topo-node-name">{{ p.name }}</span>
                    <span class="topo-node-host">{{ p.host }}</span>
                  </div>
                  <div v-if="!drTopology.standby.length" class="topo-preview-empty">无</div>
                </div>
              </div>
              <div v-if="drTopology.calls.length" class="topo-preview-calls">
                <div class="topo-preview-subtitle">进程调用关系 (CALLS)</div>
                <div v-for="(c, i) in drTopology.calls" :key="i" class="topo-preview-call">
                  {{ c.from }} → {{ c.to }}
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <div class="wiz-footer">
        <div class="wiz-footer-left">
          <el-button v-if="activeStep > 0" text size="default" @click="prevStep">
            ← {{ $t("message.common.back") }}
          </el-button>
        </div>
        <div class="wiz-footer-right">
          <el-button plain size="default" @click="visible = false">{{ $t("message.common.cancel") }}</el-button>
          <el-button
            v-if="activeStep < 1"
            type="primary"
            size="default"
            :disabled="!canNext"
            @click="nextStep"
            class="wiz-next-btn"
          >
            {{ $t("message.common.next") }} →
          </el-button>
          <el-button
            v-else
            type="primary"
            size="default"
            :loading="submitting"
            :disabled="!canSubmit"
            @click="handleCreate"
            class="wiz-create-btn"
          >
            <el-icon><CircleCheck /></el-icon> {{ $t("message.template.createTemplate") }}
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { CircleCheck, ChatDotSquare, CopyDocument, Warning } from '@element-plus/icons-vue'
import { CreateTemplate, CreateFromAi, ExportTemplate, ImportTemplate, GetTemplates, UpdateTemplate, CreateDrPipeline } from '../../api/templates'
import { GetTemplateCategories } from '../../api/template-categories'
import { useOpsflowStore } from '../../stores/opsflowStore'

const store = useOpsflowStore()
const { t } = useI18n()

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'created': [template: any]
}>()

const steps = computed(() => [
  { title: t('message.template.step1Title'), desc: t('message.template.step1Desc') },
  { title: t('message.template.step2Title'), desc: t('message.template.step2Desc') },
])

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

const method = ref<'blank' | 'ai' | 'clone' | 'dr'>('blank')
const aiPrompt = ref('')
const cloneTemplateId = ref<number | null>(null)
const drGroupId = ref<string | null>(null)
const drGroups = ref<any[]>([])
const loadingDrGroups = ref(false)
const drTopology = ref<any>(null)
const loadingTopology = ref(false)

async function onDrGroupChange(val: string) {
  if (!val) { drTopology.value = null; return }
  loadingTopology.value = true
  try {
    const { opsflowRequest } = await import('../../api/request')
    const res = await opsflowRequest({
      url: '/api/opsflow/templates/preview_dr_topology/',
      method: 'post',
      data: { dr_group_id: val },
    })
    drTopology.value = res?.data?.data || res?.data || null
  } catch {
    drTopology.value = null
  } finally {
    loadingTopology.value = false
  }
}

const projectTemplates = computed(() => (allTemplates.value || []).filter((t: any) => !t.is_public))
const publicTemplates = computed(() => (allTemplates.value || []).filter((t: any) => t.is_public))

const canNext = computed(() =>
  form.value.project_id && form.value.name.trim() && form.value.category,
)

const canSubmit = computed(() => {
  if (!form.value.project_id || !form.value.name.trim() || !form.value.category) return false
  if (method.value === 'ai' && !aiPrompt.value.trim()) return false
  if (method.value === 'clone' && !cloneTemplateId.value) return false
  if (method.value === 'dr' && !drGroupId.value) return false
  return true
})

function nextStep() { activeStep.value = 1 }
function prevStep() { activeStep.value = 0 }
function handleClose() { emit('update:modelValue', false) }

const extractData = (res: any): any => {
  if (res?.code === 2000 && res?.data) return res.data
  return res?.id ? res : res
}

async function handleCreate() {
  submitting.value = true
  if (form.value.project_id) store.setCurrentProjectId(form.value.project_id)
  try {
    let template: any

    if (method.value === 'ai') {
      const res = await CreateFromAi({ input: aiPrompt.value })
      template = extractData(res)
      if (template?.template?.id) template = template.template
      if (template?.id) {
        await UpdateTemplate(template.id, {
          name: form.value.name, category: form.value.category, description: form.value.description,
        })
        template.name = form.value.name
        template.category = form.value.category
        template.description = form.value.description
      }
    } else if (method.value === 'dr') {
      const res = await CreateDrPipeline({ dr_group_id: drGroupId.value })
      template = extractData(res)?.template || extractData(res)
      if (template?.id) {
        await UpdateTemplate(template.id, {
          name: form.value.name, category: form.value.category, description: form.value.description,
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
        name: form.value.name, category: form.value.category, description: form.value.description,
      })
      template = extractData(res)
    }

    if (!template?.id) throw new Error('Template creation returned no ID')

    ElMessage.success(t("message.template.createSuccess"))
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
  drGroupId.value = null
  drGroups.value = []

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

  // Load DrGroups (via CMDB instances API, use raw request to avoid project_id injection)
  try {
    loadingDrGroups.value = true
    const { request } = await import('/@/utils/service')
    const grpRes = await request({
      url: '/api/cmdb/instances/DrGroup/',
      method: 'get',
      params: { page_size: 200 },
    })
    // CMDB API 返回格式: {code: 2000, data: {items: [...], total: N}}
    const data = grpRes?.data?.data || grpRes?.data || grpRes || []
    const items = Array.isArray(data) ? data : (data?.items || data?.results || [])
    drGroups.value = items
    if (!items.length) {
      console.warn('[DR] No DrGroups found, raw:', grpRes)
    }
  } catch (e: any) {
    console.warn('[DR] Failed to load DrGroups:', e?.response?.data || e?.message || e)
    drGroups.value = []
  } finally {
    loadingDrGroups.value = false
  }
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

$accent: #409EFF;
$accent-dark: #337ecc;

/* ===== Layout ===== */
.create-wizard :deep(.el-dialog__body) {
  padding: 0 !important;
  min-height: 380px;
}
.create-wizard :deep(.el-dialog__footer) {
  padding: 14px 24px;
}

/* ===== Step Header ===== */
.wiz-header {
  padding: 24px 24px 0;
}
.wiz-steps {
  display: flex;
  align-items: flex-start;
  margin-bottom: 16px;
}
.wiz-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  position: relative;
  flex: 1;
}
.wiz-step-indicator {
  width: 28px;
  height: 28px;
  min-width: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  background: #f8f9fb;
  color: #c0c4cc;
  border: 2px solid #e0e0e0;
  transition: all 0.3s;
}
.wiz-step.active .wiz-step-indicator {
  background: $accent;
  color: #fff;
  border-color: $accent;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.35);
}
.wiz-step.done .wiz-step-indicator {
  background: #67C23A;
  color: #fff;
  border-color: #67C23A;
}
.wiz-step-check { font-size: 14px; }
.wiz-step-label {
  flex: 1;
  min-width: 0;
  padding-top: 3px;
}
.wiz-step-title {
  font-size: 13px;
  font-weight: 600;
  color: #c0c4cc;
  transition: color 0.3s;
}
.wiz-step.active .wiz-step-title { color: $accent; }
.wiz-step.done .wiz-step-title { color: #67C23A; }
.wiz-step-desc {
  font-size: 10px;
  color: #c0c4cc;
  margin-top: 1px;
}
.wiz-step-connector {
  flex: 1;
  height: 2px;
  background: #e8e8e8;
  margin: 13px 12px 0;
  min-width: 12px;
  transition: background 0.3s;
}
.wiz-step-connector.done { background: #67C23A; }
.wiz-progress {
  height: 3px;
  background: #f0f0f0;
  border-radius: 2px;
  margin-bottom: 0;
  overflow: hidden;
}
.wiz-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, $accent, #67C23A);
  border-radius: 2px;
  transition: width 0.4s ease;
}

/* ===== Body ===== */
.wiz-body {
  padding: 20px 24px;
  min-height: 260px;
}
.wiz-step-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ===== Panel Hero ===== */
.panel-hero {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.panel-hero-icon {
  width: 42px;
  height: 42px;
  min-width: 42px;
  border-radius: 12px;
  background: linear-gradient(135deg, #ecf5ff, #f0f8ff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.08);
}
.panel-hero-text h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: $g-text-primary;
  line-height: 1.3;
}
.panel-hero-text p {
  margin: 3px 0 0;
  font-size: 12px;
  color: $g-text-muted;
  line-height: 1.4;
}

/* ===== Form Card ===== */
.form-card {
  background: #fff;
  border: 1px solid $g-border-card;
  border-radius: 12px;
  padding: 20px 24px;
}
.form-card :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 4px;
}
.form-card :deep(.el-form-item) {
  margin-bottom: 18px;
}
.form-card :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

/* ===== Mode Selector ===== */
.mode-selector {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.mode-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: #fff;
  border: 1.5px solid #e8e8e8;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s;
}
.mode-card:hover {
  border-color: #c6e2ff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.06);
}
.mode-card.active {
  border-color: $accent;
  background: linear-gradient(135deg, #ecf5ff, #f5f9ff);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.1);
}
.mode-card-icon {
  font-size: 28px;
  flex-shrink: 0;
  width: 40px;
  text-align: center;
}
.mode-card-content { flex: 1; }
.mode-card-title {
  font-size: 14px;
  font-weight: 600;
  color: $g-text-primary;
  margin-bottom: 2px;
}
.mode-card-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
.mode-card-radio {
  width: 20px;
  height: 20px;
  min-width: 20px;
  border-radius: 50%;
  border: 2px solid #d0d0d0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s;
}
.mode-card-radio.checked {
  border-color: $accent;
  background: $accent;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15);
}
.mode-card-radio.checked::after {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
}

/* ===== Extra Card ===== */
.extra-card {
  background: #fff;
  border: 1px solid $g-border-card;
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.extra-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

/* ===== Footer ===== */
.wiz-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.wiz-footer-left, .wiz-footer-right {
  display: flex;
  gap: 10px;
  align-items: center;
}
.wiz-next-btn {
  background: linear-gradient(135deg, $accent, $accent-dark);
  border: none;
}
.wiz-next-btn:hover {
  background: linear-gradient(135deg, #60b0ff, $accent);
}
.wiz-create-btn {
  background: $g-gradient-accent;
  border: none;
}
.wiz-create-btn:hover {
  filter: brightness(1.1);
}

/* ===== Topo Preview ===== */
.topo-preview {
  margin-top: 14px;
  background: #fafbfc;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px 16px;
}
.topo-preview-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}
.topo-preview-grid {
  display: flex;
  gap: 16px;
}
.topo-preview-col {
  flex: 1;
}
.topo-preview-subtitle {
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e4e7ed;
}
.topo-preview-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  font-size: 12px;
}
.topo-node-dot {
  width: 8px;
  height: 8px;
  min-width: 8px;
  border-radius: 50%;
}
.topo-node-dot.primary { background: #409EFF; }
.topo-node-dot.standby { background: #E6A23C; }
.topo-node-name {
  font-weight: 500;
  color: #303133;
}
.topo-node-host {
  color: #909399;
  font-size: 11px;
  margin-left: auto;
}
.topo-preview-empty {
  color: #c0c4cc;
  font-size: 12px;
  padding: 4px 0;
}
.topo-preview-calls {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}
.topo-preview-call {
  font-size: 11px;
  color: #606266;
  padding: 2px 0;
  font-family: monospace;
}

/* ===== Transitions ===== */
.panel-fade-enter-active { transition: all 0.3s ease; }
.panel-fade-leave-active { transition: all 0.2s ease; }
.panel-fade-enter-from { opacity: 0; transform: translateY(10px); }
.panel-fade-leave-to { opacity: 0; }
</style>
