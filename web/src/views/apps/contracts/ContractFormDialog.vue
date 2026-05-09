<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑合约' : '新增合约'"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" label-width="120px" :rules="rules" v-loading="saving">
      <el-divider content-position="left">基本信息</el-divider>
      <el-form-item label="交易所" prop="exchange">
        <el-select v-model="form.exchange" placeholder="请选择" style="width: 100%">
          <el-option label="上期所" value="SHFE" />
          <el-option label="大商所" value="DCE" />
          <el-option label="郑商所" value="CZCE" />
          <el-option label="中金所" value="CFFEX" />
          <el-option label="广期所" value="GFEX" />
        </el-select>
      </el-form-item>
      <el-form-item label="品种代码" prop="product_code">
        <el-input v-model="form.product_code" placeholder="如: rb, MA" />
      </el-form-item>
      <el-form-item label="主力合约" prop="symbol">
        <el-input v-model="form.symbol" placeholder="如: SHFE.rb2410" />
      </el-form-item>
      <el-form-item label="合约名称" prop="name">
        <el-input v-model="form.name" placeholder="如: 螺纹钢" />
      </el-form-item>
      <el-form-item label="详细分类" prop="category">
        <el-input v-model="form.category" placeholder="如：螺纹类" />
      </el-form-item>

      <el-divider content-position="left">交易参数</el-divider>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="合约乘数" prop="volume_multiple">
            <el-input-number v-model="form.volume_multiple" :min="1" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="最小变动" prop="price_tick">
            <el-input-number v-model="form.price_tick" :min="0" :precision="4" :step="0.5" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="最小开仓手数" prop="min_position">
        <el-input-number v-model="form.min_position" :min="1" style="width: 100%" />
      </el-form-item>

      <el-divider content-position="left">状态控制</el-divider>
      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item label="交易状态" prop="is_active">
            <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="允许开仓" prop="allow_open">
            <el-switch v-model="form.allow_open" active-text="允许" inactive-text="禁止" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="夜盘交易" prop="night_trading">
            <el-switch v-model="form.night_trading" active-text="是" inactive-text="否" disabled />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { ContractRecord } from '/@/types/trading'

const props = withDefaults(defineProps<{
  modelValue: boolean
  record?: ContractRecord | null
}>(), {})

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  saved: []
}>()

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => { emit('update:modelValue', v) })

const isEdit = ref(false)
const saving = ref(false)
const formRef = ref<any>(null)

const form = reactive({
  exchange: 'SHFE',
  product_code: '',
  symbol: '',
  name: '',
  category: '',
  volume_multiple: 10,
  price_tick: 1.0,
  min_position: 1,
  is_active: false,
  allow_open: true,
  night_trading: false,
})

const rules: Record<string, any> = {
  exchange: [{ required: true, message: '请选择交易所' }],
  product_code: [{ required: true, message: '请输入品种代码' }],
  symbol: [{ required: true, message: '请输入主力合约' }],
  volume_multiple: [{ required: true, message: '请输入合约乘数' }],
}

watch(() => props.record, (r) => {
  if (r) {
    isEdit.value = true
    Object.assign(form, r)
  } else {
    isEdit.value = false
    Object.assign(form, {
      exchange: 'SHFE',
      product_code: '', symbol: '', name: '', category: '',
      volume_multiple: 10, price_tick: 1.0, min_position: 1,
      is_active: false, allow_open: true, night_trading: false,
    })
  }
}, { immediate: true })

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    // The actual save is handled by the parent through emit
    emit('saved')
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
