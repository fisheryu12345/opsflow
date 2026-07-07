# ITSM 子 Tab 组件化重构

> 提交: db5ad6f9 | 日期: 2026-07-07
> 涉及 App: itsm
> 类型: 重构

---

## 动机

ITSM 首页 `index.vue` 已膨胀到 ~1200 行，其中 tickets / workflows / sla / escalation 四个 tab 的模板、状态、函数全部内联在父组件中。这导致：

1. **维护困难** — 修改一个 tab 需要翻阅上千行代码
2. **加载不稳定** — 内联 tab 依赖父组件 `watch(activeTab)` + `onTabActivated` 手动触发 `loadXxx()`，当初始 tab 值与默认值相同时 watch 不触发，数据不加载
3. **模式不统一** — dashboard / service-market / service-admin / delegation 已经是独立组件，其余四个是内联

## 变更要点

### 重构前 vs 重构后

| 文件 | 重构前 | 重构后 |
|------|--------|--------|
| `itsm/index.vue` | ~1200 行，包含 4 个内联 tab 的全部代码 | ~250 行，4 行组件引用 |
| `itsm/TicketList.vue` | 不存在 | ~250 行，独立的工单列表组件 |
| `itsm/WorkflowList.vue` | 不存在 | ~320 行，独立的流程模板组件 |
| `itsm/SlaPolicyList.vue` | 不存在 | ~105 行，独立的 SLA 策略组件 |
| `itsm/EscalationList.vue` | 不存在 | ~175 行，独立的升级层级组件 |

### 组件契约

每个子 Tab 组件遵循统一契约：

```vue
<script setup lang="ts">
const props = withDefaults(defineProps<{ active?: boolean }>(), { active: false })
const { reportStats: updateHeroStats } = useHeroConsumer()

onMounted(() => { if (props.active) loadData() })
watch(() => props.active, (isActive) => { if (isActive && isEmpty) loadData() })

function reportStats() {
  updateHeroStats([
    { value: count, label: '标签' },
  ])
}
</script>
```

### 关键改动

1. **数据加载** — 从父组件 `onTabActivated` 回调 → 子组件 `onMounted` / `watch(active)` 自驱
2. **Stats 上报** — 从 `reportInlineStats()` → 各子组件 `useHeroConsumer().reportStats()`
3. **设计器关闭后刷新** — 从直接调 `loadWorkflows()` → 通过 `projectChangedTrigger++` 触发 tab 重挂载
4. **移除代码** — `triggerInitialLoad()`、`reportInlineStats()`、`onTabActivated`、4 组内联状态/函数
5. **共享样式** — 从 scoped `<style>` 提取到 unscoped `<style>` 块，子组件可直接使用父级 CSS 类

## 设计决策

- **为什么用 `projectChangedTrigger++` 而不是 ref 调子组件方法** — 更解耦，子组件不需要 `defineExpose`，且与项目切换复用同一重置路径
- **为什么 `watch(active)` 中检查 `isEmpty`** — 避免每次切回 tab 都重新请求；只在首次挂载（数据为空）时加载
- **为什么保留 `useTabLazyLoad`** — `v-if="isVisited()"` 的懒挂载能力仍然有效，防止 8 个组件同时初始化

## 关键文件

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/itsm/index.vue` | 父页面，简化为 Hero + 8 个组件引用 |
| `web/src/views/apps/itsm/components/TicketList.vue` | 工单列表（含筛选、分派对话框） |
| `web/src/views/apps/itsm/components/WorkflowList.vue` | 流程模板（含 AI 创建、版本管理、回滚） |
| `web/src/views/apps/itsm/components/SlaPolicyList.vue` | SLA 策略（含编辑对话框） |
| `web/src/views/apps/itsm/components/EscalationList.vue` | 升级层级（含创建/编辑对话框） |
