# Tab 懒加载架构统一 — useTabLazyLoad

> 提交: f1179192 | 日期: 2026-07-07
> 涉及 App: itsm, opsflow, cmdb, monitor, iam, integration, job-platform
> 类型: 重构 + 架构统一

---

## 动机

7 个 APP 的 Tab 切换全部使用 `v-show`，所有 Tab 在 `onMounted` 时即挂载，导致：

1. **API 请求浪费** — ITSM 12+ 并发、Job-Platform 8 并发、OPSflow 8 并发
2. **DOM 浪费** — 用户可能只访问 2-3 个 Tab，但 6-11 个 Tab 的完整 DOM 全部渲染
3. **各 APP 自行实现** — Monitor 用 `watch(activeTab)`，ITSM 用 `loadAllData()`，CMDB 用 `Promise.all(5 fetch)`，无统一模式
4. **项目切换不一致** — ITSM 用 `window.addEventListener('project-changed', loadAllData)`，OPSflow 有自己的 `onProjectChanged`

## 变更要点

### 核心模式

```html
<!-- 每个 Tab 区块统一模式 -->
<div v-if="isVisited('tickets')" v-show="activeTab === 'tickets'" class="app-section">
```

- **`v-if`** — 懒挂载核心：仅在首次访问时创建 DOM、触发子组件 `onMounted`
- **`v-show`** — 已挂载 Tab 的显示/隐藏切换，零开销
- **`isVisited()`** — `useTabLazyLoad` 提供的追踪函数

### Composable API

```ts
const { isVisited } = useTabLazyLoad({
  tabs: ['dashboard', 'tickets', ...],    // 所有 tab key
  activeTab,                              // Ref<string>
  onTabActivated: (tab, firstVisit) => {  // 首次访问时加载数据
    if (!firstVisit) return
    if (tab === 'tickets') loadTickets()
  },
  resetOn: projectChangedTrigger,         // 项目切换时重置 visitedTabs
})
```

### 按 APP 改造明细

| APP | 改造前 | 改造后 | onMount API 减少 |
|-----|--------|--------|:---:|
| **ITSM** | `loadAllData()` 4 并发 + 4 组件 `onMounted` = 12+ API | `onTabActivated` 按需 + 组件 `onMounted` 仅在访问时触发 | ~75% |
| **OPSflow** | 8 子组件全部 `v-show` 挂载，各组件 `onMounted` 触发 | `v-if=isVisited` + `resetOn` → 项目切换仅重载当前 tab | ~80% |
| **CMDB** | `Promise.all(5 store.fetch)` 全量加载 | `v-if` 懒挂载 DOM，store 数据按需 | ~70% |
| **Monitor** | `watch(activeTab)` + `v-show` | `useTabLazyLoad.onTabActivated` + `v-if` | 持平(已最优) |
| **IAM** | 11 子组件全部 `v-show` 挂载 | `v-if=isVisited`，含 `isSuperuser` 合并判断 | ~80% |
| **Integration** | `loadData()` 4 并发 | `v-if=isVisited` 懒挂载 | ~70% |
| **Job-Platform** | `Promise.all(8 load*())` 全量加载 | `v-if=isVisited` 懒挂载 | ~80% |

### 设计决策

- **为什么 `v-if` + `v-show` 组合而非单独 `v-if`** — `v-if` 控制挂载（首次访问），`v-show` 控制显示（已挂载 tab 间切换）。如果只用 `v-if`，每次切换都会销毁/重建 DOM，子组件状态丢失
- **为什么 `resetOn` 是 Ref 而非 callback** — Ref 可以被 `watch` 自动追踪，避免了手动管理 event listener 的 add/remove 配对问题
- **为什么组件 Tab 无需 `onTabActivated`** — 子组件的 `onMounted` 在 `v-if` 变为 true 时自动触发，Vue 生命周期就是懒加载机制

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/src/composables/useTabLazyLoad.ts` | 核心 composable — visitedTabs 追踪 + watch(activeTab) + resetOn |
| `web/src/views/apps/itsm/index.vue` | 首个接入方，删除 loadAllData()、componentMap |
| `web/src/views/apps/opsflow/index.vue` | 动态 `v-for` tab 模式接入示例 |
| `web/src/views/apps/monitor/index.vue` | watch→onTabActivated 迁移示例 |
| `web/src/views/apps/iam/index.vue` | isSuperuser 条件与 isVisited 合并示例 |

### 关联文档

- 相关架构文档: [2026-07-07-unified-hero-communication-refactor.md](../../opsflow/architecture/2026-07-07-unified-hero-communication-refactor.md)
- 相关功能文档: [2026-07-07-hero-search-teleport.md](../features/2026-07-07-hero-search-teleport.md)
- 前端规范: [frontend-style-guide.md](../../guides/frontend-style-guide.md)
