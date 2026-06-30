# OPSflow Frontend UI — Tab Consolidation (参考 ITSM 模式)

**Date:** 2026-06-30
**Status:** Design Approved
**Scope:** Frontend only — OPSflow 子页面合并为单一 tab 页面

## Context

当前 OPSflow 有 6+ 个独立路由和页面，每个都有自己完整的 hero + body 结构。这种分散的路由模式导致：

- 侧边栏菜单臃肿（多个 OPSflow 入口）
- 页面间跳转需要完整的路由导航
- 后续 ITSM 下拉引用 OPSflow 插件 API 需要统一的前端入口

**目标：** 参考 ITSM 的 [index.vue](../../web/src/views/apps/itsm/index.vue) 模式，将所有 OPSflow 子页面合并为一个带 hero tabs 的统一页面，单一路由 `/opsflow`。

## Design

### Route Change

| Before | After |
|--------|-------|
| `/opsflow_desgner` | → `/opsflow` (设计器 tab) |
| `/opsflow-template` | → `/opsflow` (模板中心 tab) |
| `/opsflow-execution` | → `/opsflow` (任务执行 tab) |
| `/opsflow-approval` | → `/opsflow` (审批 tab) |
| `/opsflow-knowledge` | → `/opsflow` (知识库 tab) |
| `/opsflow-log` | → `/opsflow` (执行日志 tab) |
| `/opsflow-webhook` | → `/opsflow` (Webhook tab) |
| `/ops_dashboard` | → `/opsflow` (看板 tab) |

Old routes are kept as redirects to `/opsflow` with `?tab=xxx` query param so existing bookmarks/links don't break.

### Page Structure

```
/opsflow → opsflow/index.vue
  │
  ├─ v-if="canvasMode" — 全屏设计画布
  │   └─ DesignCanvas (原 opsflow/index.vue 的画布部分)
  │
  └─ v-else — 正常 tab 视图
      ├─ Hero Section
      │   ├─ 标题: "OPSflow"
      │   ├─ 副标题: "运维流程编排与自动化"
      │   └─ 统计卡片: 模板数 / 执行数 / 审批待办 / 看板入口
      │
      ├─ Hero Tabs
      │   ├─ 设计器 (canvas)    — 点击进入 canvasMode
      │   ├─ 模板中心 (templates)
      │   ├─ 任务执行 (executions)
      │   ├─ 审批 (approvals)
      │   ├─ 知识库 (knowledge)
      │   ├─ 执行日志 (logs)
      │   ├─ Webhook (webhooks)
      │   └─ 看板 (dashboard)
      │
      └─ Body (v-show 切换)
          ├─ <Templates     v-show="activeTab === 'templates'" />
          ├─ <Executions    v-show="activeTab === 'executions'" />
          ├─ <Approvals     v-show="activeTab === 'approvals'" />
          ├─ <Knowledge     v-show="activeTab === 'knowledge'" />
          ├─ <Logs          v-show="activeTab === 'logs'" />
          ├─ <Webhooks      v-show="activeTab === 'webhooks'" />
          └─ <Dashboard     v-show="activeTab === 'dashboard'" />
```

### Tab Content Strategy

每个 tab 的内容来自现有子页面的 **body 部分**（去掉各自独立的 hero），作为独立组件嵌入：

| Tab | 原页面 | 嵌入方式 |
|-----|--------|---------|
| 设计器 | `opsflow/index.vue` | 点击 tab → `canvasMode = true`，全屏显示 DesignCanvas |
| 模板中心 | `opsflow-template/index.vue` | 提取 body 部分为 `<OPSflowTemplates>` 组件 |
| 任务执行 | `opsflow-execution/index.vue` | 提取 body + ExecutionList/Detail 为 `<OPSflowExecutions>` 组件 |
| 审批 | `opsflow-approval/index.vue` | 提取 body 为 `<OPSflowApprovals>` 组件 |
| 知识库 | `opsflow-knowledge/index.vue` | 提取 body 为 `<OPSflowKnowledge>` 组件 |
| 执行日志 | `opsflow-log/index.vue` | 提取 body 为 `<OPSflowLogs>` 组件 |
| Webhook | `opsflow-webhook/index.vue` | 提取 body 为 `<OPSflowWebhooks>` 组件 |
| 看板 | `opsflow-dashboard/index.vue` | 提取 body 为 `<OPSflowDashboard>` 组件 |

**组件提取策略：** 优先复用各子页面已有的内部组件（如 `ExecutionList`、`ExecutionDetail`），无需修改原子页面即可在新 tab 页面中嵌入。若子页面逻辑写在 `index.vue` 内部未抽组件，则提取 body 部分为独立 `components/*Body.vue` 子组件，原页面和新 tab 页面共用。

### 设计器 Canvas 模式

```
点击 "设计器" tab
  → canvasMode = true
  → 隐藏 hero + tabs
  → 全屏显示 DesignCanvas（原 opsflow/index.vue 的画布 + AI 对话浮窗）
  → 画布顶部有 "← 返回" 按钮
  → 点击返回 → canvasMode = false → 回到 tab 视图
```

这与 ITSM 的 `designerMode` 模式完全一致。

### Hero Stats 聚合

统一 hero 的统计数字从各 tab 的数据源聚合。初始加载时只拉取基本统计（模板数、执行数、待审批数），各 tab 的详细数据在切换到对应 tab 时才加载（懒加载）。

```
模板数   ← GET /api/opsflow/templates/?page_size=1 取 count
执行数   ← GET /api/opsflow/executions/?page_size=1 取 count
待审批   ← GET /api/opsflow/approvals/pending-count/
```

### URL Query 支持

- `/opsflow?tab=templates` → 直接进入模板中心 tab
- `/opsflow?tab=executions&id=123` → 进入任务执行 tab 并打开 id=123 的执行详情
- 旧路由 `/opsflow-template?xxx` → redirect `/opsflow?tab=templates&xxx`

### Menu Seed 更新

`backend/opsflow/management/commands/seed_opsflow.py` 中：

- 删除独立菜单项: 运维管理、看板大屏、任务执行、项目管理、知识库、模板中心
- 新增单一菜单项: "运维管理" → `web_path=/opsflow`, `component=apps/opsflow/index`
- 审批/日志/webhook 之前未入菜单，无需处理

### Key Design Decisions

1. **v-show 而非 v-if** — 保持各 tab 的组件实例存活，切换回来时保留滚动位置和状态（跟 ITSM 一致）
2. **懒加载数据** — 只有切换到某 tab 时才触发其数据请求，减少首屏加载
3. **旧路由保留为 redirect** — 不破坏已有书签和外部链接
4. **设计器 canvas 不受 tab 影响** — canvas 全屏模式下与 tab UI 完全隔离
5. **不修改任何后端 API** — 纯前端改造

## Files to Modify

| File | Change |
|------|--------|
| `web/src/views/apps/opsflow/index.vue` | **重写** — 新的统一 tab 页面，包含 hero + tabs + 各子页面嵌入 |
| `web/src/views/apps/opsflow-template/index.vue` | **轻改** — 提取 body 为可导出组件 |
| `web/src/views/apps/opsflow-execution/index.vue` | **轻改** — 提取 body 为可导出组件 |
| `web/src/views/apps/opsflow-approval/index.vue` | **轻改** — 提取 body 为可导出组件 |
| `web/src/views/apps/opsflow-knowledge/index.vue` | **轻改** — 提取 body 为可导出组件 |
| `web/src/views/apps/opsflow-log/index.vue` | **轻改** — 提取 body 为可导出组件 |
| `web/src/views/apps/opsflow-webhook/index.vue` | **轻改** — 提取 body 为可导出组件 |
| `web/src/views/apps/opsflow-dashboard/index.vue` | **轻改** — 提取 body 为可导出组件 |
| `web/src/router/backEnd.ts` or menu DB | 旧路由标记为 redirect 或 deprecate |
| `backend/opsflow/management/commands/seed_opsflow.py` | 菜单种子合并为单项 |

## Verification

1. **页面加载** — 访问 `/opsflow`，看到 hero + tabs，默认显示第一个 tab
2. **Tab 切换** — 点击不同 tab，内容切换，状态保留
3. **设计器模式** — 点击"设计器"tab → 全屏画布 → 点返回 → 回到 tab 视图
4. **URL 参数** — `/opsflow?tab=templates` 直接打开模板 tab
5. **旧路由兼容** — 访问 `/opsflow-template` → 自动跳转到 `/opsflow?tab=templates`
6. **侧边栏菜单** — 只显示一个"运维管理"入口
7. **审批/日志/webhook** — 各 tab 功能正常
8. **i18n** — 所有新增文本走 i18n
