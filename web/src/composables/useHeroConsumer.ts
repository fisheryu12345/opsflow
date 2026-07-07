import { inject, type Ref } from 'vue'
import { HERO_STATS_KEY, HERO_FILTER_KEY, HERO_SEARCH_KEY, type HeroStatItem } from './useHeroProvider'

/**
 * Child component composable: consumes hero stats + Teleport targets from the parent.
 * Call in sub-tab components that need to report stats or Teleport content into the hero.
 * All injects have safe fallbacks — the component still works when rendered standalone.
 */
export function useHeroConsumer() {
  const stats = inject<HeroStatItem[]>(HERO_STATS_KEY)
  const filterEl = inject<Ref<HTMLElement | null> | null>(HERO_FILTER_KEY, null)
  const searchEl = inject<Ref<HTMLElement | null> | null>(HERO_SEARCH_KEY, null)

  function reportStats(items: HeroStatItem[]) {
    if (!stats) return
    stats.length = 0
    stats.push(...items)
  }

  return { stats, filterEl, searchEl, reportStats }
}
