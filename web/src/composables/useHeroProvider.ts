import { ref, reactive, provide, type Ref } from 'vue'

export interface HeroStatItem {
  value: number | string
  label: string
}

/** Symbol keys for provide/inject — avoids string collision */
export const HERO_STATS_KEY = Symbol('heroStats')
export const HERO_FILTER_KEY = Symbol('heroFilter')
export const HERO_SEARCH_KEY = Symbol('heroSearch')

/**
 * Parent page composable: provides hero stats + Teleport targets to child components.
 * Call once in the app shell (e.g., itsm/index.vue, opsflow/index.vue).
 */
export function useHeroProvider() {
  const stats = reactive<HeroStatItem[]>([])
  const filterRef = ref<HTMLElement | null>(null)
  const searchRef = ref<HTMLElement | null>(null)

  provide(HERO_STATS_KEY, stats)
  provide(HERO_FILTER_KEY, filterRef)
  provide(HERO_SEARCH_KEY, searchRef)

  function updateStats(items: HeroStatItem[]) {
    stats.length = 0
    stats.push(...items)
  }

  return { stats, filterRef, searchRef, updateStats }
}
