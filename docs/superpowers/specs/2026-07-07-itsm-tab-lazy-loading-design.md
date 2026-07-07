# ITSM Sub-Tab Lazy Loading Optimization

**Date:** 2026-07-07
**Status:** Draft
**Author:** Claude

## Problem

The ITSM page (`web/src/views/apps/itsm/index.vue`) mounts all 8 sub-tabs simultaneously using `v-show`, causing:

1. **Excessive API calls on mount** — `loadAllData()` fires 4 parallel requests (tickets, workflows, SLA, escalation), while sub-components (Dashboard, ServiceMarket, ServiceAdmin, Delegation) each fire their own `onMounted` requests. Total: 8+ concurrent API calls on page load.
2. **Tab rendering failures** — heavy concurrent load leads to occasional timeouts; when one request fails, the user perceives the whole tab as "not loading."
3. **Unnecessary resource usage** — tabs the user never visits are still fully mounted, executing their entire lifecycle.
4. **Project switching overhead** — `project-changed` event re-fires all data loads regardless of which tab is active.

## Solution

Adopt a **"render on first visit, then toggle visibility"** strategy — a standard Vue pattern already used in the Monitor module (`monitor/index.vue:327`).

### Core Mechanism

- Wrap each tab section with `v-if="visitedTabs.includes(tabKey)" v-show="activeTab === tabKey"`
- Track visited tabs via a `visitedTabs` ref array
- On mount: load only the active tab's data; sub-components' `onMounted` fires naturally when `v-if` becomes true
- On tab switch: mark as visited, trigger data load for inline tabs
- On project switch: clear `visitedTabs` → current tab unmounts and remounts → data re-fetches

## Change Scope

**Only one file changes:** `web/src/views/apps/itsm/index.vue`

Not touched: `Dashboard.vue`, `ServiceMarket.vue`, `ServiceAdmin.vue`, `Delegation.vue`, API layer, backend, routes.


## Detailed Changes

### 1. Template: Add `v-if` to all 8 tab sections

Each tab section gains `v-if="visitedTabs.includes('<key>')"` while keeping the existing `v-show`:

```diff
-<div v-show="activeTab === 'dashboard'" class="itsm-section g-fade-in-up">
+<div v-if="visitedTabs.includes('dashboard')" v-show="activeTab === 'dashboard'" class="itsm-section g-fade-in-up">
```

Apply to all 8 tabs (keys: `dashboard`, `service-market`, `service-admin`, `tickets`, `workflows`, `sla`, `delegation`, `escalation`).

### 2. Script: Add visited-tab tracking

```ts
const visitedTabs = ref<string[]>([])

function markVisited(tab: string) {
  if (!visitedTabs.value.includes(tab)) {
    visitedTabs.value.push(tab)
  }
}
```

### 3. Script: Unified onTabClick with visit tracking

```diff
 function onTabClick(tab: any) {
   if (!tab.has_access) { ... return }
+  markVisited(tab.key)
   activeTab.value = tab.key
 }
```

### 4. Script: watch(activeTab) for on-demand data loading

```ts
watch(activeTab, (tab) => {
  markVisited(tab)
  if (tab === 'tickets') loadTickets()
  else if (tab === 'workflows') loadWorkflows()
  else if (tab === 'sla') loadSla()
  else if (tab === 'escalation') loadEscalation()
  // Component tabs (dashboard / service-market / service-admin / delegation):
  // their own onMounted fires automatically when v-if becomes true
})
```

### 5. Script: Simplified onMounted

```diff
 onMounted(async () => {
   await loadPageConfig()
-  await loadAllData()
+  markVisited(activeTab.value)
+  if (activeTab.value === 'tickets') await loadTickets()
+  else if (activeTab.value === 'workflows') await loadWorkflows()
+  else if (activeTab.value === 'sla') await loadSla()
+  else if (activeTab.value === 'escalation') await loadEscalation()

-  window.addEventListener('project-changed', loadAllData)
+  window.addEventListener('project-changed', onProjectChanged)
 })

 onBeforeUnmount(() => {
-  window.removeEventListener('project-changed', loadAllData)
+  window.removeEventListener('project-changed', onProjectChanged)
 })
```

### 6. Script: Project-switch handler

```diff
-async function loadAllData() {
-  await Promise.all([loadTickets(), loadWorkflows(), loadSla(), loadEscalation()])
+function onProjectChanged() {
+  visitedTabs.value = []          // unmount all tabs
+  markVisited(activeTab.value)    // remount current tab only
+  if (activeTab.value === 'tickets') loadTickets()
+  else if (activeTab.value === 'workflows') loadWorkflows()
+  else if (activeTab.value === 'sla') loadSla()
+  else if (activeTab.value === 'escalation') loadEscalation()
 }
```

### 7. Remove unused code

- Delete the `loadAllData()` function entirely.
- The `componentMap` object (lines 467-472) is also dead code and can be removed.

## How Sub-Components Handle Data Loading

The 4 component tabs (Dashboard, ServiceMarket, ServiceAdmin, Delegation) each already implement their own `onMounted` with data-fetching logic. When `v-if` transitions from `false` to `true` (first click), Vue automatically:

1. Mounts the component
2. Fires `onMounted`
3. Data loads and renders

No changes needed — Vue's lifecycle IS the lazy loading mechanism.

## Behavioral Changes

| Scenario | Before | After |
|---|---|---|
| Page mount | 8+ concurrent API calls | `pageConfig` + ~1 tab API call |
| Switch to Dashboard | v-show toggle (DOM exists) | First: mount + onMounted; Subsequent: v-show toggle |
| Switch to Tickets | v-show toggle | First: mount + loadTickets(); Subsequent: v-show toggle |
| Project switch | reloadAllData() → 4+ reqs | clear visitedTabs → current tab remounts (1-2 reqs) |
| Error handling | 1 failure shadows other tabs | Only affected tab shows error; other tabs untouched |

## Verification

1. Open ITSM page → only the default tab's data should be fetched (observe Network tab)
2. Click each tab → first click triggers component mount + data loading; subsequent clicks are instant (v-show)
3. Switch projects → current tab unmounts and remounts; other tabs load only when visited
4. Verify Monitor module still works (no regressions — used as reference pattern)
5. No TypeScript or ESLint errors
