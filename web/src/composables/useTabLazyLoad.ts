import { ref, watch, onMounted, type Ref } from 'vue'

export interface UseTabLazyLoadOptions {
  /** All available tab keys */
  tabs: string[]
  /** Reactive active tab ref */
  activeTab: Ref<string>
  /** Called when a tab becomes active. `isFirstVisit` = true on first activation after mount/reset. */
  onTabActivated?: (tab: string, isFirstVisit: boolean) => void | Promise<void>
  /** Optional external trigger to reset visitedTabs (e.g., project change) */
  resetOn?: Ref<any>
}

export function useTabLazyLoad(options: UseTabLazyLoadOptions) {
  const visitedTabs = ref<string[]>([])

  function isVisited(tab: string): boolean {
    return visitedTabs.value.includes(tab)
  }

  function markVisited(tab: string) {
    if (!visitedTabs.value.includes(tab)) {
      visitedTabs.value.push(tab)
    }
  }

  function reset() {
    visitedTabs.value = []
    markVisited(options.activeTab.value)
  }

  // Mark the default active tab as visited on mount
  onMounted(() => {
    markVisited(options.activeTab.value)
  })

  // Watch tab switches: mark visited + trigger data loading callback
  watch(options.activeTab, (newTab) => {
    const firstVisit = !isVisited(newTab)
    markVisited(newTab)
    options.onTabActivated?.(newTab, firstVisit)
  })

  // Watch external reset trigger (e.g., project change)
  if (options.resetOn) {
    watch(options.resetOn, () => {
      reset()
      options.onTabActivated?.(options.activeTab.value, true)
    })
  }

  return { visitedTabs, isVisited, markVisited, reset }
}
