# OPSflow 前端设计

## 页面结构

主入口 `web/src/views/apps/opsflow/index.vue`，通过 vue-next-admin 的后端菜单管理系统注册以下子页面：

| 页面路由 | 目录 | 用途 |
|---|---|---|
| opsflow | `apps/opsflow/` | 主设计画布（index.vue + DesignCanvas + AI 聊天浮窗） |
| opsflow-template | `apps/opsflow-template/` | 模板管理列表（CRUD、搜索、分类筛选） |
| opsflow-execution | `apps/opsflow-execution/` | 执行历史列表 + 实时监控画布（MonitorCanvas） |
| opsflow-approval | `apps/opsflow-approval/` | 待审批节点列表（含审批/拒绝操作） |
| opsflow-dashboard | `apps/opsflow-dashboard/` | 仪表盘（统计图表 + 趋势 + 排名） |
| opsflow-log | `apps/opsflow-log/` | 操作日志审计 |
| opsflow-knowledge | `apps/opsflow-knowledge/` | 知识库管理 |
| opsflow-project | `apps/opsflow-project/` | 项目管理（成员管理、权限） |
| opsflow-webhook | `apps/opsflow-webhook/` | Webhook 配置列表 |
| opsflow-stats | `apps/opsflow-stats/` | 深度统计报表 |

## 组件层次

```
opsflow/index.vue
 ├── DesignCanvas.vue           # 设计模式画布（X6 Graph）
 │    ├── ProjectSwitcher.vue   # 项目切换器
 │    ├── PropertyPanel.vue     # 属性面板（节点/边选中时显示）
 │    ├── GlobalVariablePanel.vue # 全局变量面板（左侧滑出）
 │    ├── SchemeSelector.vue    # 执行方案选择器
 │    ├── SubprocessStatusBadge.vue # 子流程状态徽标
 │    └── ConditionDialog.vue   # 条件表达式编辑弹窗
 │         └── ConditionRow.vue # 条件规则行（字段、运算符、值）
 ├── MonitorCanvas.vue          # 监控画布（WebSocket 实时更新）
 │    └── SchemeManager.vue     # 执行方案管理弹窗
 ├── PluginPickerDialog.vue     # 插件选择器弹窗
 ├── PluginVisibilityDialog.vue # 插件可见性配置
 ├── CreateTemplateWizard.vue   # 新建模板向导（分步弹窗）
 ├── SubmitWizardDialog.vue     # 提交执行向导（变量确认/方案选择）
 ├── DryRunDialog.vue           # Dry Run 实时监控弹窗
 ├── DiffModal.vue              # AI 生成 vs 当前画布 Diff
 ├── VariableBrowser.vue        # 变量浏览器
 ├── VariablePicker.vue         # 变量选择器（嵌入属性面板）
 ├── HelpDrawer.vue             # 帮助侧边栏（使用指南）
 └── ProjectEnvVarPanel.vue     # 项目环境变量面板
```

## X6 节点类型

9 种自定义形状定义在 `shapes.ts`：

| 形状名称 | 类型 | 外观 | 端口 |
|---|---|---|---|
| `ops-start-event` | 圆形（56x56） | 绿色底色 + ▶ 图标 | 右出 |
| `ops-end-event` | 圆形（56x56） | 红色底色 + ■ 图标 | 左入 |
| `ops-atom` | 卡片（208x56） | 白色底色 + 分组色边框 | 上下左右 |
| `ops-subprocess` | 卡片（208x56） | 浅蓝底色 + 蓝色虚边 | 上下左右 |
| `ops-exclusive-gateway` | 菱形（70x70） | ⊗ 图标（橙色） | 上下左右 |
| `ops-parallel-gateway` | 菱形（70x70） | ⊞ 图标（蓝色） | 上下左右 |
| `ops-conditional-parallel-gateway` | 菱形（70x70） | ◐ 图标（浅蓝） | 上下左右 |
| `ops-converge-gateway` | 菱形（70x70） | ⨁ 图标（灰色） | 上下左右 |
| `ops-approval` | 菱形（70x70） | ✓ 图标（紫色） | 上下左右 |

边样式统一：描边 `#DCDFE6`，线宽 1.5，箭头 classic，支持条件标签。

## 调色板分组

Stencil 面板从后端插件系统动态加载，按 `group` 字段分组：

| 分组 | 图标 | 颜色 | 后端插件目录 |
|---|---|---|---|
| 通用工具 | ⚙ | #409EFF | `plugins/common/` |
| HTTP | ↔ | #67C23A | `plugins/http/` |
| CMDB | ◈ | #19BE6B | `plugins/cmdb/` |
| Ansible | ▶ | #E6A23C | `plugins/ansible/` |
| ITSM | ☷ | #5CADFF | `plugins/itsm/` |
| Monitor | ◉ | #F56C6C | `plugins/monitor/` |
| ESXi | ☰ | #9B59B6 | `plugins/esxi/` |
| Redfish | ≈ | #00BCD4 | `plugins/redfish/` |
| ServiceNow | ✉ | #FF9800 | `plugins/servicenow/` |
| NetApp | ◇ | #607D8B | `plugins/netapp/` |
| Pmax | ▲ | #795548 | `plugins/pmax/` |
| 验证工具 | ✓ | #67C23A | `plugins/verify/` |

## 数据流

```
 ┌─────────────┐      REST API      ┌───────────────┐
 │ Django 后端  │ ◄──────────────── │ Pinia Store   │
 │ (DRF 视图)   │                   │ (opsflowStore) │
 └──────┬──────┘                   └───────┬───────┘
        │ WebSocket (channel layer)        │
        ▼                                  ▼
 ┌─────────────┐                   ┌───────────────┐
 │ useMonitor  │──────────────────▶│  DesignCanvas  │
 │ (实时状态)   │  reactive refs   │  / MonitorCanvas│
 └─────────────┘                   └───────────────┘
```

- **Pinia Store** (`stores/opsflowStore.ts`): 管理 mode（design/monitor）、currentTemplate、currentExecution、projects、globalVariables
- **DesignCanvas** → 读取 store 的 currentTemplate.pipeline_tree → 渲染 X6 Graph
- **MonitorCanvas** → useMonitor WebSocket → 逐节点更新颜色/状态
- **ProjectSwitcher** → 切换 projectId → 触发 store.fetchMyProjects() → 刷新模板列表
- AI 对话 → index.vue 的 chatMessages → CreateFromAi / RefinePipeline API → 更新画布

## Composable 架构

| Composable | 功能 | 依赖 |
|---|---|---|
| `useGraphCanvas` | 通用 Graph 实例创建（design/monitor/preview 模式）、网格/平移/滚轮、连线验证规则、撤销/重做、导出 | X6 Graph |
| `useDesignCanvas` | 设计模式增强：Stencil 调色板、拖放创建节点、属性面板绑定、全局变量面板、AI 布局、节点删除 | useGraphCanvas |
| `useMonitor` | WebSocket 连接管理、节点状态跟踪、心跳保活、自动重连 | 原生 WebSocket |
| `useGraphValidator` | 拓扑验证：开始/结束节点、孤立节点、死路径、未配置原子节点、边条件引用检查 | useGraphCanvas |
| `useAutoSave` | 定期自动保存草稿（防丢）、脏标志检测 | useDesignCanvas |

## API 客户端

`web/src/api/opsflow/` 包含 13 个 API 文件：

| 文件 | 端点前缀 | 主要方法 |
|---|---|---|
| `request.ts` | - | opsflowRequest 实例、createCrudApi 工厂、prefix 常量 |
| `templates.ts` | `/templates/` | CRUD + CreateFromAi + RefinePipeline + AnalyzePipeline + AiLayout + Diff + ConfirmDraft |
| `executions.ts` | `/executions/` | StartExecution + GetExecutionDetail + NodeActions + SubprocessExecute |
| `plugins.ts` | `/plugins/` | CRUD + GetPluginForm |
| `projects.ts` | `/projects/` | CRUD + GetMyProjects + Members |
| `dashboard.ts` | `/dashboard/` | Stats + Trend + ScheduleStats + TopTemplates + StatusDistribution + NodeTypeDistribution |
| `logs.ts` | `/logs/` | CRUD |
| `knowledge.ts` | `/knowledge/` | CRUD |
| `schedule-plans.ts` | `/schedule-plans/` | CRUD + Enable/Disable |
| `webhooks.ts` | `/webhooks/` | CRUD |
| `audit.ts` | `/audit/` | CRUD |
| `servicenow.ts` | - | ServiceNow 审批状态查询 |
| `template-categories.ts` | `/template-categories/` | CRUD |

## 样式系统

### 变量定义 `styles/opsflow-variables.scss`

- 颜色：`$of-color-primary` (#409EFF)、`$of-bg-page`、`$of-text-primary`、`$of-border-default`
- 圆角：`$of-radius-sm` (8px)、`$of-radius-card` (10px)、`$of-radius-lg` (12px)
- 渐变：`$of-gradient-blue`、`$of-gradient-accent`、`$of-gradient-hero`
- 阴影：`$of-shadow-card`、`$of-shadow-hover`、`$of-shadow-primary`
- 间距/内边距：`$of-padding-card`、`$of-padding-dialog-header`

### 全局样式 `styles/opsflow-global.scss`

- `.of-card` — 标准卡片容器
- `.of-fade-in-up` / `.of-stagger-item` — 入场动画
- `@mixin of-dialog-header/body/footer` — 弹窗段落样式
- `@mixin of-hover-lift` / `of-hover-shift` — 悬停动效
- `@mixin of-icon-circle` — 渐变圆形图标

### OPSFLOW.md 规范

- 类名：kebab-case，组件前缀（如 `mycomp-header`）
- Dialog：必须加 `class="opsflow-dialog"`
- 空状态：`<el-empty :image-size="40" />`
- 加载：`v-loading` + `element-loading-text`
- SCSS 导入：每个组件内 `@import '../styles/opsflow-global';`
- 命名：CSS 类使用组件前缀 + 语义名，避免全局冲突
