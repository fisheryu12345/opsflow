import { ref, reactive, watch } from 'vue'
import * as api from './api'

export interface ToolCallLog {
  tool_name: string
  arguments: Record<string, any>
  assessment?: {
    score: number
    decision: string
    reason: string
  }
  status: string
  result: string | null
  error: string | null
}

export interface RunResult {
  session_id: string
  user_input: string
  output: string
  status: string
  tool_calls: ToolCallLog[]
}

export function useConsole() {
  const input = ref('')
  const running = ref(false)
  const result = ref<RunResult | null>(null)
  const error = ref('')
  const history = ref<{ input: string; result: RunResult | null; error: string }[]>([])

  async function execute() {
    const cmd = input.value.trim()
    if (!cmd || running.value) return

    running.value = true
    error.value = ''
    result.value = null

    try {
      const res = await api.RunTask(cmd)
      if (res.code === 2000) {
        result.value = res.data as RunResult
        history.value.unshift({ input: cmd, result: result.value, error: '' })
      } else {
        error.value = res.msg || '执行失败'
        history.value.unshift({ input: cmd, result: null, error: error.value })
      }
    } catch (e: any) {
      const msg = e?.message || '请求失败'
      error.value = msg
      history.value.unshift({ input: cmd, result: null, error: msg })
    } finally {
      running.value = false
    }
  }

  function clearResult() {
    result.value = null
    error.value = ''
  }

  function loadHistory(item: { input: string; result: RunResult | null; error: string }) {
    input.value = item.input
    result.value = item.result
    error.value = item.error
  }

  return { input, running, result, error, history, execute, clearResult, loadHistory }
}
