<template>
  <el-dialog v-model="visible" title="Request Permission" width="420px" top="15vh" destroy-on-close append-to-body @closed="reset">
    <el-alert type="info" :closable="false" style="margin-bottom:14px">
      You don't have permission for: <b>{{ permissionLabel }}</b>
    </el-alert>
    <el-form label-width="80px" size="small">
      <el-form-item label="Permission">
        <el-input :model-value="permissionKey" disabled />
      </el-form-item>
      <el-form-item label="Reason" required>
        <el-input v-model="reason" type="textarea" :rows="2" placeholder="Why do you need this?" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button size="small" @click="visible = false">Cancel</el-button>
      <el-button size="small" type="primary" :loading="submitting" @click="submit">Submit Request</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { request } from '/@/utils/service'

const visible = ref(false)
const permissionKey = ref('')
const permissionLabel = ref('')
const reason = ref('')
const submitting = ref(false)

function open(key: string, label: string) {
  permissionKey.value = key
  permissionLabel.value = label || key
  reason.value = ''
  visible.value = true
}

function reset() {
  permissionKey.value = ''
  permissionLabel.value = ''
  reason.value = ''
}

async function submit() {
  if (!reason.value) { ElMessage.warning('Please enter a reason'); return }
  submitting.value = true
  try {
    await request({
      url: '/api/iam/requests/',
      method: 'post',
      data: {
        request_type: 'menu_button',
        target_menu_button_value: permissionKey.value,
        reason: `[Auto-request] ${permissionLabel.value}: ${reason.value}`,
      },
    })
    ElMessage.success('Permission request submitted')
    visible.value = false
  } catch (e: any) { ElMessage.error(e?.msg || 'Failed to submit request') }
  submitting.value = false
}

// Listen for global permission request events from v-can directive
function onGlobalRequest(e: CustomEvent) {
  open(e.detail.key, e.detail.label)
}

onMounted(() => window.addEventListener('iam:request-permission', onGlobalRequest as EventListener))
onBeforeUnmount(() => window.removeEventListener('iam:request-permission', onGlobalRequest as EventListener))

defineExpose({ open })
</script>
