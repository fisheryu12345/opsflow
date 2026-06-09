<template>
  <el-dialog :model-value="visible" title="创建监控策略" width="900px" top="3vh" :close-on-click-modal="false"
    :before-close="handleClose" class="strategy-wizard-dialog" @update:model-value="emit('close')">
    <!-- Step progress -->
    <el-steps :active="activeStep" finish-status="success" align-center style="margin-bottom: 24px;">
      <el-step title="基本信息" description="Basic Info" />
      <el-step title="监控项" description="Monitoring Item" />
      <el-step title="检测配置" description="Detect Config" />
      <el-step title="通知与创建" description="Notification" />
    </el-steps>

    <el-form ref="formRef" :model="form" label-width="110px" size="default"
      style="min-height: 380px; padding: 0 20px;">

      <!-- Step 1: Basic Info -->
      <div v-show="activeStep === 0">
        <h3 style="margin-bottom: 16px; color: #303133;">基本信息</h3>
        <el-form-item label="策略名称" prop="name" :rules="[{ required: true, message: '请输入策略名称', trigger: 'blur' }]">
          <el-input v-model="form.name" placeholder="例如: 生产服务器CPU告警" maxlength="128" show-word-limit />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="业务ID" prop="bk_biz_id"
              :rules="[{ required: true, message: '请输入业务ID', trigger: 'blur' }]">
              <el-input-number v-model="form.bk_biz_id" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="监控场景" prop="scenario"
              :rules="[{ required: true, message: '请选择场景', trigger: 'change' }]">
              <el-select v-model="form.scenario" style="width:100%">
                <el-option label="主机监控" value="host" />
                <el-option label="服务监控" value="service" />
                <el-option label="自定义监控" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="策略类型" prop="type">
          <el-radio-group v-model="form.type">
            <el-radio value="monitor">监控</el-radio>
            <el-radio value="fta">故障自愈</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="策略描述（选填）" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create default-first-option
            placeholder="输入标签后回车" style="width:100%">
            <el-option v-for="tag in tagOptions" :key="tag" :label="tag" :value="tag" />
          </el-select>
        </el-form-item>
      </div>

      <!-- Step 2: Monitoring Item + Query Config -->
      <div v-show="activeStep === 1">
        <h3 style="margin-bottom: 16px; color: #303133;">监控项与查询配置</h3>
        <el-divider content-position="left">监控项</el-divider>
        <el-form-item label="监控项名称" prop="itemName"
          :rules="[{ required: true, message: '请输入监控项名称', trigger: 'blur' }]">
          <el-input v-model="form.itemName" placeholder="例如: CPU使用率" />
        </el-form-item>
        <el-divider content-position="left">查询配置</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="数据来源" prop="dataSourceLabel"
              :rules="[{ required: true, message: '请选择数据源', trigger: 'change' }]">
              <el-select v-model="form.dataSourceLabel" style="width:100%">
                <el-option label="Prometheus" value="prometheus" />
                <el-option label="InfluxDB" value="influxdb" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="数据类型" prop="dataTypeLabel">
              <el-select v-model="form.dataTypeLabel" style="width:100%">
                <el-option label="指标 (Metric)" value="metric" />
                <el-option label="事件 (Event)" value="event" />
                <el-option label="日志 (Log)" value="log" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="指标ID" prop="metricId"
              :rules="[{ required: true, message: '请输入指标ID', trigger: 'blur' }]">
              <el-autocomplete v-model="form.metricId" :fetch-suggestions="queryMetricSuggestions"
                placeholder="例如: cpu_usage_pct" style="width:100%" clearable />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="查询语句 (PromQL)">
          <el-input v-model="form.promql" type="textarea" :rows="2"
            placeholder='例如: 100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)' />
          <div style="font-size:12px;color:#909399;margin-top:4px;">
            PromQL 语法提示: rate() / irate() / avg() / sum() / by() 等
          </div>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="聚合间隔">
              <el-input-number v-model="form.aggInterval" :min="10" :step="10" :max="3600" style="width:100%">
                <template #suffix><span style="font-size:12px;">秒</span></template>
              </el-input-number>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="别名">
              <el-input v-model="form.alias" placeholder="例如: cpu_usage" maxlength="12" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Step 3: Detect Config + Algorithm -->
      <div v-show="activeStep === 2">
        <h3 style="margin-bottom: 16px; color: #303133;">检测与算法配置</h3>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="告警级别" prop="severity"
              :rules="[{ required: true, message: '请选择级别', trigger: 'change' }]">
              <el-select v-model="form.severity" style="width:100%">
                <el-option label="致命" :value="1" />
                <el-option label="预警" :value="2" />
                <el-option label="提醒" :value="3" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="持续次数" prop="triggerCount">
              <el-input-number v-model="form.triggerCount" :min="1" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="检测窗口" prop="checkWindow">
              <el-input-number v-model="form.checkWindow" :min="1" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="算法类型" prop="algorithmType"
          :rules="[{ required: true, message: '请选择算法', trigger: 'change' }]">
          <el-select v-model="form.algorithmType" style="width:100%" @change="onAlgorithmChange">
            <el-option-group label="阈值类">
              <el-option label="静态阈值" value="Threshold" />
              <el-option label="简易环比" value="SimpleRingRatio" />
              <el-option label="高级环比" value="AdvancedRingRatio" />
              <el-option label="简易同比" value="SimpleYearRound" />
              <el-option label="高级同比" value="AdvancedYearRound" />
            </el-option-group>
            <el-option-group label="智能类">
              <el-option label="智能异常检测" value="IntelligentDetect" />
              <el-option label="时序预测" value="TimeSeriesForecasting" />
            </el-option-group>
            <el-option-group label="可用性">
              <el-option label="主机重启" value="OsRestart" />
              <el-option label="Ping不可达" value="PingUnreachable" />
              <el-option label="进程端口" value="ProcPort" />
            </el-option-group>
          </el-select>
        </el-form-item>

        <!-- Algorithm-specific parameter form -->
        <el-card v-if="algorithmParamsVisible" shadow="never" style="margin-top:8px; background:#fafafa;">
          <template #header>
            <span style="font-weight:500;">算法参数</span>
          </template>
          <el-form-item label="比较方法" v-if="showCompareMethod">
            <el-select v-model="form.algorithmConfig.method" style="width:100%">
              <el-option label="大于等于 (>=)" value="gte" />
              <el-option label="大于 (>)" value="gt" />
              <el-option label="小于等于 (<=)" value="lte" />
              <el-option label="小于 (<)" value="lt" />
              <el-option label="等于 (=)" value="eq" />
            </el-select>
          </el-form-item>
          <el-form-item label="阈值" v-if="showThreshold">
            <el-input-number v-model="form.algorithmConfig.threshold" :min="0" :precision="2" style="width:100%" />
          </el-form-item>
          <el-form-item label="浮动范围" v-if="showFloatRange">
            <el-input-number v-model="form.algorithmConfig.floor" :min="0" :precision="2" style="width:100%" />
          </el-form-item>
        </el-card>

        <el-form-item label="算法连接符" style="margin-top:8px;">
          <el-radio-group v-model="form.connector">
            <el-radio value="and">AND</el-radio>
            <el-radio value="or">OR</el-radio>
          </el-radio-group>
          <div style="font-size:12px;color:#909399;margin-left:8px;">多个算法条件之间的关系</div>
        </el-form-item>
      </div>

      <!-- Step 4: Notification + Action + Review -->
      <div v-show="activeStep === 3">
        <h3 style="margin-bottom: 16px; color: #303133;">通知与创建</h3>
        <el-form-item label="通知方式">
          <el-checkbox-group v-model="form.notifyChannels">
            <el-checkbox label="email">邮件</el-checkbox>
            <el-checkbox label="wecom">企业微信</el-checkbox>
            <el-checkbox label="dingtalk">钉钉</el-checkbox>
            <el-checkbox label="sms">短信</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="通知组">
          <el-select v-model="form.notifyGroupIds" multiple placeholder="选择通知组" style="width:100%">
            <el-option v-for="g in notifyGroups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作插件">
          <el-select v-model="form.actionPluginId" placeholder="选择告警触发后执行的动作" style="width:100%" clearable>
            <el-option v-for="p in actionPlugins" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">配置预览</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="策略名称">{{ form.name }}</el-descriptions-item>
          <el-descriptions-item label="业务ID">{{ form.bk_biz_id }}</el-descriptions-item>
          <el-descriptions-item label="场景">{{ scenarioLabel }}</el-descriptions-item>
          <el-descriptions-item label="监控项">{{ form.itemName }}</el-descriptions-item>
          <el-descriptions-item label="数据来源">{{ dataSourceLabel }}</el-descriptions-item>
          <el-descriptions-item label="指标ID">{{ form.metricId }}</el-descriptions-item>
          <el-descriptions-item label="告警级别">{{ severityLabel }}</el-descriptions-item>
          <el-descriptions-item label="算法">{{ algorithmLabel }}</el-descriptions-item>
          <el-descriptions-item label="通知方式" :span="2">{{ notifyLabel || '未配置' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-form>

    <!-- Footer buttons -->
    <template #footer>
      <div style="display:flex; justify-content:space-between;">
        <div>
          <el-button v-if="activeStep > 0" @click="prevStep">上一步</el-button>
        </div>
        <div>
          <el-button @click="handleClose">取消</el-button>
          <el-button v-if="activeStep < 3" type="primary" @click="nextStep">
            {{ activeStep === 3 ? '完成创建' : '下一步' }}
          </el-button>
          <el-button v-if="activeStep === 3" type="primary" :loading="submitting" @click="submitForm">
            确认创建
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox, FormInstance } from 'element-plus'
import { strategyApi } from '/@/api/monitor/index'

// ── Props & Emits ──
const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'created'): void }>()

// ── State ──
const activeStep = ref(0)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const notifyGroups = ref<any[]>([])
const actionPlugins = ref<any[]>([])
const tagOptions = ref<string[]>(['host', 'service', 'critical', 'warning'])

const form = reactive({
  name: '',
  bk_biz_id: 2,
  scenario: 'host',
  type: 'monitor',
  description: '',
  tags: [] as string[],
  // Item
  itemName: '',
  // Query Config
  dataSourceLabel: 'prometheus',
  dataTypeLabel: 'metric',
  metricId: '',
  promql: '',
  aggInterval: 60,
  alias: '',
  // Detect Config
  severity: 3,
  triggerCount: 3,
  checkWindow: 5,
  connector: 'and',
  // Algorithm
  algorithmType: 'Threshold',
  algorithmConfig: reactive({
    method: 'gte',
    threshold: 80,
    floor: 0,
  }),
  // Notification
  notifyChannels: [] as string[],
  notifyGroupIds: [] as number[],
  actionPluginId: null as number | null,
})

// ── Computed ──
const scenarioLabel = computed(() => {
  const map: Record<string, string> = { host: '主机监控', service: '服务监控', custom: '自定义监控' }
  return map[form.scenario] || form.scenario
})
const dataSourceLabel = computed(() => {
  const map: Record<string, string> = { prometheus: 'Prometheus', influxdb: 'InfluxDB', custom: '自定义' }
  return map[form.dataSourceLabel] || form.dataSourceLabel
})
const severityLabel = computed(() => {
  const map: Record<number, string> = { 1: '致命', 2: '预警', 3: '提醒' }
  return map[form.severity] || '-'
})
const algorithmLabel = computed(() => {
  const algoMap: Record<string, string> = {
    Threshold: '静态阈值', SimpleRingRatio: '简易环比', AdvancedRingRatio: '高级环比',
    SimpleYearRound: '简易同比', AdvancedYearRound: '高级同比',
    IntelligentDetect: '智能异常检测', TimeSeriesForecasting: '时序预测',
    OsRestart: '主机重启', PingUnreachable: 'Ping不可达', ProcPort: '进程端口',
  }
  return algoMap[form.algorithmType] || form.algorithmType
})
const notifyLabel = computed(() => {
  if (!form.notifyChannels.length) return ''
  return form.notifyChannels.map((c: string) => ({ email: '邮件', wecom: '企业微信', dingtalk: '钉钉', sms: '短信' }[c] || c)).join(', ')
})

// Algorithm UI helpers
const algorithmParamsVisible = computed(() =>
  ['Threshold', 'SimpleRingRatio', 'AdvancedRingRatio', 'SimpleYearRound', 'AdvancedYearRound'].includes(form.algorithmType)
)
const showCompareMethod = computed(() =>
  ['Threshold', 'SimpleRingRatio', 'AdvancedRingRatio'].includes(form.algorithmType)
)
const showThreshold = computed(() =>
  ['Threshold'].includes(form.algorithmType)
)
const showFloatRange = computed(() =>
  ['SimpleRingRatio', 'AdvancedRingRatio', 'SimpleYearRound', 'AdvancedYearRound'].includes(form.algorithmType)
)

// ── Methods ──
function onAlgorithmChange(val: string) {
  // Reset algorithm config when type changes
  form.algorithmConfig.method = 'gte'
  form.algorithmConfig.threshold = 80
  form.algorithmConfig.floor = 0
}

async function queryMetricSuggestions(query: string, cb: (results: { value: string }[]) => void) {
  // Mock autocomplete — in production, call a /api/monitor/metrics/suggest endpoint
  const commonMetrics = [
    { value: 'cpu_usage_pct' },
    { value: 'mem_usage_pct' },
    { value: 'disk_usage_pct' },
    { value: 'disk_read_bytes' },
    { value: 'disk_write_bytes' },
    { value: 'net_recv_bytes' },
    { value: 'net_sent_bytes' },
    { value: 'load_avg_1m' },
    { value: 'tcp_conn_count' },
    { value: 'http_request_rate' },
  ]
  if (!query) return cb(commonMetrics)
  cb(commonMetrics.filter(m => m.value.includes(query.toLowerCase())))
}

async function loadNotifyGroups() {
  try {
    const r = await (await import('/@/api/monitor/index')).notifyGroupApi.list()
    notifyGroups.value = r.data || []
  } catch { /* ignore */ }
}

async function loadActionPlugins() {
  try {
    const r = await (await import('/@/api/monitor/index')).actionPluginApi.list()
    actionPlugins.value = r.data || []
  } catch { /* ignore */ }
}

async function validateStep(step: number): Promise<boolean> {
  if (!formRef.value) return false
  if (step === 0) {
    return new Promise((resolve) => {
      formRef.value!.validateField(['name', 'bk_biz_id', 'scenario'], (err) => resolve(!err))
    })
  }
  if (step === 1) {
    return new Promise((resolve) => {
      formRef.value!.validateField(['itemName', 'dataSourceLabel', 'metricId'], (err) => resolve(!err))
    })
  }
  if (step === 2) {
    return new Promise((resolve) => {
      formRef.value!.validateField(['severity', 'algorithmType'], (err) => resolve(!err))
    })
  }
  return true
}

async function nextStep() {
  const valid = await validateStep(activeStep.value)
  if (!valid) {
    ElMessage.warning('请完善当前步骤的必填项')
    return
  }
  if (activeStep.value < 3) activeStep.value++
}

function prevStep() {
  if (activeStep.value > 0) activeStep.value--
}

async function submitForm() {
  submitting.value = true
  try {
    // Build the nested payload expected by the backend
    const payload = {
      name: form.name,
      bk_biz_id: form.bk_biz_id,
      scenario: form.scenario,
      type: form.type,
      description: form.description,
      tags: form.tags,
      items: [
        {
          name: form.itemName,
          expression: form.promql,
          metric_type: form.metricId,
          query_configs: [
            {
              alias: form.alias || form.itemName.toLowerCase().replace(/\s+/g, '_'),
              data_source_label: form.dataSourceLabel,
              data_type_label: form.dataTypeLabel,
              metric_id: form.metricId,
              config: {
                promql: form.promql,
                agg_interval: form.aggInterval,
              },
            },
          ],
          detect_configs: [
            {
              level: form.severity,
              connector: form.connector,
              trigger_config: {
                count: form.triggerCount,
                check_window: form.checkWindow,
              },
              algorithms: [
                {
                  type: form.algorithmType,
                  level: form.severity,
                  config: { ...form.algorithmConfig },
                },
              ],
            },
          ],
        },
      ],
      notify: {
        channels: form.notifyChannels,
        group_ids: form.notifyGroupIds,
        action_plugin_id: form.actionPluginId,
      },
    }
    const r = await strategyApi.create(payload)
    if (r.code === 2000 || r.code === 200) {
      ElMessage.success('策略创建成功')
      emit('created')
      emit('close')
    } else {
      ElMessage.error(r.msg || '创建失败')
    }
  } catch (err: any) {
    ElMessage.error(err?.msg || '创建策略异常')
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  if (activeStep.value > 0) {
    ElMessageBox.confirm('确认关闭？尚未保存的配置将丢失。', '提示', {
      confirmButtonText: '确认关闭',
      cancelButtonText: '继续编辑',
      type: 'warning',
    }).then(() => {
      resetForm()
      emit('close')
    }).catch(() => { /* continue editing */ })
  } else {
    resetForm()
    emit('close')
  }
}

function resetForm() {
  activeStep.value = 0
  form.name = ''
  form.bk_biz_id = 2
  form.scenario = 'host'
  form.type = 'monitor'
  form.description = ''
  form.tags = []
  form.itemName = ''
  form.dataSourceLabel = 'prometheus'
  form.dataTypeLabel = 'metric'
  form.metricId = ''
  form.promql = ''
  form.aggInterval = 60
  form.alias = ''
  form.severity = 3
  form.triggerCount = 3
  form.checkWindow = 5
  form.connector = 'and'
  form.algorithmType = 'Threshold'
  form.algorithmConfig.method = 'gte'
  form.algorithmConfig.threshold = 80
  form.algorithmConfig.floor = 0
  form.notifyChannels = []
  form.notifyGroupIds = []
  form.actionPluginId = null
}

onMounted(() => {
  loadNotifyGroups()
  loadActionPlugins()
})
</script>

<style scoped lang="scss">
.strategy-wizard-dialog {
  :deep(.el-dialog__body) {
    padding: 20px 24px;
  }
  :deep(.el-step__title) {
    font-size: 13px;
  }
  :deep(.el-divider__text) {
    font-size: 13px;
    font-weight: 500;
  }
}
</style>
