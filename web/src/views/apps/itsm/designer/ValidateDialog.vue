<template>
  <el-dialog
    v-model="visible"
    :title="$t('message.designer.validateTitle')"
    width="580px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <!-- Summary bar -->
    <div class="vd-summary" :class="allPass ? 'vd-all-pass' : 'vd-has-errors'">
      <span v-if="allPass">✅ {{ $t('message.designer.validateAllPass', { n: checks.length }) }}</span>
      <span v-else>❌ {{ $t('message.designer.validateFailCount', { n: failCount }) }}</span>
    </div>

    <!-- Check item list -->
    <div class="vd-list">
      <div
        v-for="check in checks"
        :key="check.rule"
        class="vd-item"
        :class="{ 'vd-fail': check.status === 'fail' }"
      >
        <div class="vd-item-header">
          <span class="vd-icon">
            <el-icon v-if="check.status === 'pass'" color="#67C23A" :size="18"><CircleCheck /></el-icon>
            <el-icon v-else color="#F56C6C" :size="18"><CircleClose /></el-icon>
          </span>
          <span class="vd-message">{{ check.message }}</span>
        </div>
        <p v-if="check.suggestion" class="vd-suggestion">💡 {{ check.suggestion }}</p>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">{{ $t('message.designer.validateClose') }}</el-button>
      <el-button v-if="allPass" type="primary" @click="handleDeploy" :loading="deploying">
        {{ $t('message.designer.confirmDeploy') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { CircleCheck, CircleClose } from '@element-plus/icons-vue'

export interface CheckItem {
  rule: string
  status: 'pass' | 'fail'
  message: string
  suggestion: string
}

const props = defineProps<{
  checks: CheckItem[]
}>()

const emit = defineEmits<{
  close: []
  deploy: []
}>()

const visible = ref(true)
const deploying = ref(false)

const allPass = computed(() => props.checks.every(c => c.status === 'pass'))
const failCount = computed(() => props.checks.filter(c => c.status === 'fail').length)

function handleClose() {
  visible.value = false
  emit('close')
}

async function handleDeploy() {
  deploying.value = true
  emit('deploy')
}
</script>

<style scoped>
.vd-summary {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 16px;
}
.vd-all-pass {
  background: #f0f9eb;
  color: #67C23A;
}
.vd-has-errors {
  background: #fef0f0;
  color: #F56C6C;
}
.vd-list {
  max-height: 420px;
  overflow-y: auto;
}
.vd-item {
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
}
.vd-item.vd-fail {
  background: #fef0f0;
  border-color: #fab6b6;
}
.vd-item-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.vd-icon {
  margin-top: 1px;
  flex-shrink: 0;
}
.vd-message {
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
  word-break: break-all;
}
.vd-suggestion {
  margin: 6px 0 0 26px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}
</style>
