# 统一 Hero 组件通信 — Symbol-based provide/inject

> 提交: f1179192 | 日期: 2026-07-07
> 涉及 App: opsflow, itsm
> 类型: 重构

---

## 动机

OPSflow 使用字符串 key (`'updateHeroStats'`, `'heroFilterEl'`, `'heroSearchEl'`) 做 `provide`/`inject`，存在以下问题：

1. **命名冲突风险** — 字符串 key 在大型项目中可能意外碰撞
2. **类型不安全** — 8 个子组件各自手写 `inject<any>('updateHeroStats', () => {})`，签名不统一
3. **不可发现** — 新开发者不知道有哪些 key 可用，只能 copy-paste 已有组件
4. **copy-paste 碎片化** — 每个子组件重复相同的 import + inject 模板代码

## 变更要点

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `opsflow/index.vue` | `provide('updateHeroStats', fn)` + `provide('heroFilterEl', ref)` + `provide('heroSearchEl', ref)` | `useHeroProvider()` — 一行调用，返回 `{ stats, filterRef, searchRef, updateStats }` |
| 8 个 opsflow 子组件 | `inject<any>('updateHeroStats', () => {})` + `inject<any>('heroFilterEl', null)` | `useHeroConsumer()` — `const { reportStats: updateHeroStats, filterEl, searchEl }` |
| `itsm/index.vue` | 无 provide/inject（hero stats 硬编码 `tickets.length`） | `useHeroProvider()` — 动态 `heroStats` reactive 数组 + `searchRef` Teleport 目标 |
| `itsm/ServiceMarket.vue` | 搜索框在 body 内 | `useHeroConsumer()` → `searchEl` Teleport 到 hero |
| `itsm/ServiceAdmin.vue` | 同 ServiceMarket | 同 ServiceMarket，加 `active` prop 守卫防止多 tab Teleport 冲突 |

### 代码对比

```ts
// 重构前 — OPSflow 父组件（字符串 key，不安全）
provide('updateHeroStats', (stats) => { heroStats.length = 0; heroStats.push(...stats) })
provide('heroFilterEl', heroFilterRef)
provide('heroSearchEl', heroSearchRef)

// 重构前 — OPSflow 子组件（每个文件手写 inject）
const updateHeroStats = inject<(s: any) => void>('updateHeroStats', () => {})
const heroFilterEl = inject<any>('heroFilterEl', null)
const heroSearchEl = inject<any>('heroSearchEl', null)
```

```ts
// 重构后 — 父组件（Symbol key，类型安全，一行）
const { stats: heroStats, searchRef, filterRef, updateStats } = useHeroProvider()

// 重构后 — 子组件（同样一行，带类型推导）
const { reportStats: updateHeroStats, filterEl, searchEl } = useHeroConsumer()
```

```html
<!-- 重构前 — ITSM hero stats 硬编码 -->
<div class="itsm-hero-stats">
  <div class="itsm-stat-item">
    <span>{{ tickets.length }}</span>
    <span>工单</span>
  </div>
</div>

<!-- 重构后 — ITSM hero stats 动态渲染 -->
<div class="itsm-hero-stats">
  <template v-for="(stat, i) in heroStats" :key="i">
    <div v-if="i > 0" class="itsm-stat-divider" />
    <div class="itsm-stat-item">
      <span class="itsm-stat-value">{{ stat.value }}</span>
      <span class="itsm-stat-label">{{ stat.label }}</span>
    </div>
  </template>
</div>
```

### 设计决策

- **为什么用 Symbol 而非字符串** — Symbol 天然防冲突，且 TypeScript 可通过 `typeof HERO_STATS_KEY` 推导类型
- **为什么拆成 Provider / Consumer 两个 composable** — 职责清晰：Provider 是父页面调用的"出口"，Consumer 是子组件调用的"入口"。子组件可以独立渲染（inject 带 fallback `null`）
- **为什么 Consumer 的 `reportStats` 需要别名** — 多个子组件内部有自己的 `reportStats()` 包装函数（汇总数据后再上报），避免命名冲突

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/src/composables/useHeroProvider.ts` | Provider composable — `provide()` HeroStatItem[] + 2 个 Teleport DOM ref |
| `web/src/composables/useHeroConsumer.ts` | Consumer composable — `inject()` 带 `null` fallback |
| `web/src/views/apps/opsflow/index.vue` | 首个接入方，provide 迁移 |
| `web/src/views/apps/itsm/index.vue` | 动态 hero stats + search Teleport 目标 |
| `web/src/views/apps/itsm/catalog/ServiceMarket.vue` | 搜索框 Teleport 示例 |
| `web/src/views/apps/itsm/catalog/ServiceAdmin.vue` | 搜索框 Teleport + `active` 守卫示例 |

### 关联文档

- 相关功能文档: [2026-07-07-hero-search-teleport.md](../../itsm/features/2026-07-07-hero-search-teleport.md)
- 相关架构文档: [2026-07-07-tab-lazy-loading-refactor.md](../../itsm/architecture/2026-07-07-tab-lazy-loading-refactor.md)
