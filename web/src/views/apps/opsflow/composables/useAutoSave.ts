import { ref, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'

export function useAutoSave(
  saveFn: (data: any) => Promise<void>,
  getDataFn: () => any,
  options?: { intervalMs?: number; debounceMs?: number },
) {
  const INTERVAL = options?.intervalMs ?? 60000  // 60s
  const DEBOUNCE = options?.debounceMs ?? 3000    // 3s

  const lastSaveAt = ref<Date | null>(null)
  const isSaving = ref(false)
  const unsavedChanges = ref(false)
  const enabled = ref(true)

  let timer: ReturnType<typeof setInterval> | null = null
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  function markChanged() {
    unsavedChanges.value = true
    // 防抖：连续编辑后 3s 才允许触发自动保存
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      debounceTimer = null
    }, DEBOUNCE)
  }

  async function forceSave() {
    if (isSaving.value) return
    isSaving.value = true
    try {
      const data = getDataFn()
      await saveFn(data)
      lastSaveAt.value = new Date()
      unsavedChanges.value = false
    } catch {
      ElMessage.error('Auto-save failed')
    } finally {
      isSaving.value = false
    }
  }

  function pause() { enabled.value = false }
  function resume() { enabled.value = true }

  function start() {
    timer = setInterval(async () => {
      if (!enabled.value || isSaving.value || !unsavedChanges.value) return
      // 防抖期间跳过
      if (debounceTimer) return
      await forceSave()
    }, INTERVAL)
  }

  function destroy() {
    if (timer) { clearInterval(timer); timer = null }
    if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null }
  }

  onBeforeUnmount(() => destroy())

  return { lastSaveAt, isSaving, unsavedChanges, markChanged, forceSave, start, pause, resume, destroy }
}
