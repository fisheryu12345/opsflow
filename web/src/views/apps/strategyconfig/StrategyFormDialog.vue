<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑策略配置' : '新建策略配置'"
    width="700px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" label-width="150px" :rules="rules" v-loading="saving">
      <el-tabs type="border-card">
        <el-tab-pane label="资金管理">
          <el-form-item label="所属账户">
            <el-tag type="info">{{ currentAccountLabel }}</el-tag>
            <div class="form-helper">策略自动绑定到当前账户，保存后不可变更</div>
          </el-form-item>
          <el-form-item label="配置名称" prop="name">
            <el-input v-model="form.name" placeholder="例如: 海龟策略_标准版" />
          </el-form-item>
          <el-form-item label="最大持仓单位" prop="max_units">
            <el-input-number v-model="form.max_units" :min="1" :max="10" style="width: 100%" />
            <div class="form-helper">单个品种最多持有N个Unit，固定上限防过度集中。默认: 3</div>
          </el-form-item>
          <el-form-item label="初始建仓单位" prop="entry_units">
            <el-input-number v-model="form.entry_units" :min="1" :max="5" style="width: 100%" />
            <div class="form-helper">首次开仓固定1 Unit，后续通过加仓增加。默认: 1</div>
          </el-form-item>
          <el-form-item label="每单位风险金额(元)" prop="risk_per_unit">
            <el-input-number v-model="form.risk_per_unit" :min="0" :precision="2" :step="500" style="width: 100%" />
            <div class="form-helper">决定开仓手数：unit_lots = 风险金额 / (ATR × 2 × 合约乘数)。默认: 4000</div>
          </el-form-item>
          <el-form-item label="ATR风险倍数" prop="position_risk_multiplier">
            <el-input-number v-model="form.position_risk_multiplier" :min="1" :max="5" style="width: 100%" />
            <div class="form-helper">止损距离基准倍数 = N × ATR。默认: 2</div>
          </el-form-item>
          <el-form-item label="保本启用比例" prop="protect_cost_enabled_ratio">
            <el-input-number v-model="form.protect_cost_enabled_ratio" :min="0.5" :max="10" :precision="2" :step="0.5" style="width: 100%" />
            <div class="form-helper">盈利超过 N×ATR 时自动启用保本价保护。默认: 2.5</div>
          </el-form-item>
          <el-form-item label="订单超时(秒)" prop="timeout_seconds">
            <el-input-number v-model="form.timeout_seconds" :min="10" :max="300" style="width: 100%" />
            <div class="form-helper">TargetPosTask等待成交的超时时间。默认: 60</div>
          </el-form-item>
        </el-tab-pane>

        <el-tab-pane label="技术指标">
          <el-form-item label="ATR周期" prop="atr_period">
            <el-input-number v-model="form.atr_period" :min="5" :max="100" style="width: 100%" />
            <div class="form-helper">平均真实波幅的计算周期。默认: 20</div>
          </el-form-item>
          <el-form-item label="入场突破周期" prop="entry_period">
            <el-input-number v-model="form.entry_period" :min="5" :max="100" style="width: 100%" />
            <div class="form-helper">唐奇安通道突破周期。默认: 20</div>
          </el-form-item>
          <el-form-item label="均线周期" prop="ma_periods">
            <el-input v-model="form.ma_periods" placeholder="逗号分隔，如: 10,20,40" />
            <div class="form-helper">用于计算趋势因子，逗号分隔三组均线。默认: 10,20,40</div>
          </el-form-item>
        </el-tab-pane>

        <el-tab-pane label="趋势因子">
          <el-form-item label="封顶上限" prop="trend_gap_limit">
            <el-input-number v-model="form.trend_gap_limit" :min="0.001" :max="0.1" :precision="4" :step="0.005" style="width: 100%" />
            <div class="form-helper">均线间距达此比例时trend_factor封顶。默认: 0.03 (3%)</div>
          </el-form-item>
          <el-form-item label="趋势因子最大值" prop="trend_factor_max">
            <el-input-number v-model="form.trend_factor_max" :min="0" :max="1" :precision="3" :step="0.1" style="width: 100%" />
            <div class="form-helper">trend_factor上限。止损倍数范围=[2.0, 2×(1+此值)]。默认: 0.5</div>
          </el-form-item>
          <el-form-item label="强趋势阈值" prop="trend_label_strong_ratio">
            <el-input-number v-model="form.trend_label_strong_ratio" :min="0" :max="1" :precision="3" :step="0.05" style="width: 100%" />
            <div class="form-helper">trend_strength≥此值时标签显示strong。默认: 0.80</div>
          </el-form-item>
          <el-form-item label="弱趋势阈值" prop="trend_label_weak_ratio">
            <el-input-number v-model="form.trend_label_weak_ratio" :min="0" :max="1" :precision="3" :step="0.05" style="width: 100%" />
            <div class="form-helper">trend_strength≥此值时标签显示weak。默认: 0.30</div>
          </el-form-item>
        </el-tab-pane>

        <el-tab-pane label="过滤参数">
          <el-form-item label="跳空放弃阈值(%)" prop="gap_threshold">
            <el-input-number v-model="form.gap_threshold" :min="0" :max="10" :precision="2" :step="0.1" style="width: 100%" />
            <div class="form-helper">跳空幅度=abs(最新价-昨收)/ATR，超过此值跳过开仓。默认: 1.5</div>
          </el-form-item>
        </el-tab-pane>

        <el-tab-pane label="TqSDK配置">
          <el-form-item label="TqSDK账号" prop="tqapi_account">
            <el-input v-model="form.tqapi_account" placeholder="请输入天勤量化账号" />
          </el-form-item>
          <el-form-item label="TqSDK密码" prop="tqapi_password">
            <el-input v-model="form.tqapi_password" type="password" show-password placeholder="请输入密码" />
          </el-form-item>
        </el-tab-pane>
      </el-tabs>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { StrategyConfigRecord } from '/@/types/trading'
import { useAccountStore } from '/@/stores/account'

const accountStore = useAccountStore()

const currentAccountLabel = computed(() => {
  const a = accountStore.accounts.find(a => a.id === form.account)
  return a ? `${a.name} (ID: ${a.id})` : `账户 #${form.account}`
})

const props = withDefaults(defineProps<{
  modelValue: boolean
  record?: StrategyConfigRecord | null
}>(), {})

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  saved: [form: Partial<StrategyConfigRecord>]
}>()

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => { emit('update:modelValue', v) })

const isEdit = ref(false)
const saving = ref(false)
const formRef = ref<any>(null)

const form = reactive({
  account: accountStore.currentAccountId || 0,
  name: '',
  max_units: 3,
  entry_units: 1,
  risk_per_unit: 4000,
  position_risk_multiplier: 2,
  protect_cost_enabled_ratio: 2.5,
  timeout_seconds: 60,
  atr_period: 20,
  entry_period: 20,
  ma_periods: '10,20,40',
  trend_gap_limit: 0.03,
  trend_factor_max: 0.5,
  trend_label_strong_ratio: 0.80,
  trend_label_weak_ratio: 0.30,
  gap_threshold: 1.5,
  tqapi_account: '',
  tqapi_password: '',
})

const rules: Record<string, any> = {
  name: [{ required: true, message: '请输入配置名称' }],
  tqapi_account: [{ required: true, message: '请输入TqSDK账号' }],
}

watch(() => props.record, (r) => {
  if (r) {
    isEdit.value = true
    Object.assign(form, r)
  } else {
    isEdit.value = false
    Object.assign(form, {
      account: accountStore.currentAccountId || 0,
      name: '', max_units: 3, entry_units: 1, risk_per_unit: 4000,
      position_risk_multiplier: 2, protect_cost_enabled_ratio: 2.5,
      timeout_seconds: 60, atr_period: 20, entry_period: 20,
      ma_periods: '10,20,40', trend_gap_limit: 0.03, trend_factor_max: 0.5,
      trend_label_strong_ratio: 0.80, trend_label_weak_ratio: 0.30,
      gap_threshold: 1.5, tqapi_account: '', tqapi_password: '',
    })
  }
}, { immediate: true })

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!form.account) {
    ElMessage.warning('未找到交易账户，无法创建策略')
    return
  }
  saving.value = true
  try {
    emit('saved', { ...form })
    visible.value = false
    ElMessage.success(isEdit.value ? '已更新' : '已创建')
  } finally {
    saving.value = false
  }
}

function handleClose() {
  formRef.value?.resetFields()
}
</script>

<style scoped>
.form-helper {
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.4;
  margin-top: 4px;
}
</style>
