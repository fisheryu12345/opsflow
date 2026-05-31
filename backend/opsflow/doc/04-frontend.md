# 前端设计

## 页面结构

```
index.vue (OpsFlow 主页面)
│
├── AI Chat 浮窗 (chat-float-panel)
│   ├── 消息历史列表
│   ├── 加载指示器
│   └── 输入框 + Send 按钮
│
├── 模板选择栏 (template-bar)
│   └── el-select 下拉选择模板
│
├── DesignCanvas (设计画布)
│   ├── 工具栏 (浮动右上角)
│   │   ├── Undo / Redo
│   │   ├── Zoom In / Zoom Out / Fit
│   │   ├── Diff / AI Analyze / AI Layout
│   │   ├── New Template
│   │   └── Save
│   ├── Stencil 组件面板 (左侧, 可折叠)
│   │   ├── Test 组 (1)
│   │   ├── Check 组 (3)
│   │   ├── Action 组 (8)
│   │   ├── Control 组 (2)
│   │   ├── VM (ESXi) 组 (5)
│   │   ├── Storage (NetApp) 组 (5)
│   │   ├── ITSM (ServiceNow) 组 (5)
│   │   ├── BMC (Redfish) 组 (7)
│   │   ├── Generic 组 (1)
│   │   └── Gateway/Event 组 (6)
│   ├── X6 Graph 画布
│   ├── Minimap (右下小地图)
│   └── PropertyPanel (右侧属性面板)
│
├── MonitorCanvas (监控画布)
│   ├── 状态栏 (状态标签 + WebSocket 连接指示)
│   └── X6 Graph (只读, 实时着色 + Tower 进度)
│
├── New Template Dialog
├── AI Analyze Dialog
└── Diff Modal

## 其他页面

### 审计日志页 (web/src/views/apps/opsflow-log/index.vue)
- 白卡片容器 + 搜索/筛选栏
- 表格列：ID / Step 步骤 / Command 命令 / 风险等级（状态点着色: low=#67C23A, medium=#E6A23C, high/critical=#F56C6C）/ 审批人 / 创建时间
- View 图标按钮查看详情

### 知识库页 (web/src/views/apps/opsflow-knowledge/index.vue)
- 白卡片容器 + 搜索/筛选栏
- 表格列：Title 标题 / Content 内容 / 标签 / 来源 / 创建时间
- Edit/Delete 图标按钮（inline）

### 模板管理页 (web/src/views/apps/opsflow-template/index.vue)
- 双视图（表格视图 / 卡片视图）切换
- 表格列：名称 / 状态（草稿/已发布标签）/ 创建人 / 更新时间
- 管道列：缩微管道流程图（▶ 开始/绿、◉ 任务/蓝、■ 结束/红、◆ 网关/灰、⚙ Ansible/绿、↗ HTTP/橙、🖥 ESXi/青）
- 卡片视图：每个模板一张卡片 + 状态标签 + 创建信息
- 查看弹窗：垂直管道流程图（完整节点/连线渲染）

### 执行记录页 (web/src/views/apps/opsflow-execution/index.vue)
- 标签过滤栏（全部 / 运行中 / 已完成 / 失败 / 已取消 / 已暂停）
- 表格：模板名称 / 状态（着色标签）/ 创建人 / 开始时间 / 结束时间 / 操作
- 执行详情页 (ExecutionDetail.vue)：嵌入 MonitorCanvas 实时监控 + WebSocket 状态同步

### Dashboard 统计页 (web/src/views/apps/opsflow-dashboard/index.vue)
- 7 统计卡片（总执行 / 运行中 / 已完成 / 失败 / 模板 / 成功率 / 平均耗时）
- ECharts 4 图表：
  - 执行趋势折线图（30 天，梯度填充，完成/失败/总览）
  - 状态分布环形图（padAngle + borderRadius 圆角/Completed/Failed/Running/Paused/Cancelled）
  - Top 模板水平条形图（按执行次数排序 Top 8）
  - 节点类型分布环形图（Ansible/HTTP/ServiceNow/ESXi/Other）
- 用户活跃度表格（用户名 / 执行次数 / 模板数 / 最后活跃时间）
- 系统概览区（总节点数 / 活跃用户占比进度条）
```

## 自定义 X6 节点

| 图形 | Shape 名称 | 外观 | 使用 |
|------|-----------|------|------|
| `ops-atom` | Rect 圆角矩形 | 蓝边 180×48 | 所有原子操作 |
| `ops-start-event` | Circle 圆形 | 绿边 56×56 | 流程起点 |
| `ops-end-event` | Circle 圆形 | 红边 56×56 | 流程终点 |
| `ops-exclusive-gateway` | Diamond 菱形 | 橙色 (×) 70×70 | 排他网关 |
| `ops-parallel-gateway` | Diamond 菱形 | 蓝色 (+) 70×70 | 并行网关 |
| `ops-conditional-parallel-gateway` | Diamond 菱形 | 青色 (✓) 70×70 | 条件并行 |
| `ops-converge-gateway` | Diamond 菱形 | 灰色 (⊕) 70×70 | 汇聚网关 |

### 节点连接桩 (Ports)

所有节点默认连接桩 `opacity: 0`，mouseenter 时显示，mouseleave 时隐藏。

| 节点 | 连接桩 |
|------|--------|
| ops-atom | top / bottom / left / right (各 1) |
| ops-start-event | out (右侧) |
| ops-end-event | in (左侧) |
| 网关 | top / bottom / left / right (各 1) |

## X6 插件使用

| 插件 | 用途 |
|------|------|
| History | Undo/Redo (Ctrl+Z/Y) |
| Snapline | 对齐辅助线 |
| Clipboard | 复制粘贴 (Ctrl+C/V) |
| Selection | 框选 (rubberband) |
| MiniMap | 小地图导航 |
| Keyboard | 快捷键 (Del/Backspace 删除) |
| Stencil | 左侧组件面板 |

## Stencil 分组

当前画布 Stencil 共 10 个分组，包含 37 个原子节点 + 6 个网关/事件节点：

### 原子节点 (ops-atom)

| 分组 | 节点 | 数量 | 用途 |
|------|------|------|------|
| Test | Print Time | 1 | 流程引擎功能验证 |
| Check | Disk Check / Ping Test / Health Check | 3 | 系统检查前置 |
| Action | Shell / Upload File / Copy File / Run Script / Backup File / Deploy App / Docker Deploy / Nginx Reload | 8 | 运维操作 |
| Control | Service Control / Send Alert | 2 | 服务/告警控制 |
| VM (ESXi) | Create VM / Destroy VM / Power On / Power Off / VM State | 5 | 虚拟机管理 |
| Storage (NetApp) | Create Volume / Delete Volume / Modify Volume / Get Volume / Create Snapshot | 5 | 存储管理 |
| ITSM (ServiceNow) | Create Incident / Update Incident / Get Incident / Change Request / Get CMDB CI | 5 | IT 服务管理 |
| BMC (Redfish) | System Info / Power On / Power Off / Power Cycle / Set Boot Device / List Storage / Firmware Inventory | 7 | 裸金属管理 |
| Generic | HTTP API Call | 1 | 通用 REST 调用 |

### 网关/事件节点

| 分组 | 节点 | 数量 |
|------|------|------|
| Gateway | Start / End / Condition? / Parallel / Cond. Parallel / Converge | 6 |

## 数据流

```
用户输入自然语言
    │
    ▼
CreateFromAi API → 返回 pipeline_tree
    │
    ▼
loadGraphData(data) → X6 渲染节点和连线
    │
    ▼
用户在画布拖拽编辑
    │
    ▼
getGraphData() → {nodes, edges}
    │
    ▼
Save → UpdateTemplate API
    │
    ▼
选择模板 → GetTemplateDetail → loadGraphData
```

## 状态管理 (Pinia)

```typescript
interface OpsflowState {
  mode: 'design' | 'monitor'
  currentTemplate: FlowTemplate | null
  currentExecution: FlowExecution | null
  templates: FlowTemplate[]
  executions: FlowExecution[]
}
```

## WebSocket 监控

```
MonitorCanvas 连接:
  ws://host/ws/opsflow/execution/{id}/

消息类型:
  init_state: { node_status, status }            ← 连接初始状态快照
  node_status: { node_id, status, message }      ← 节点状态变更
  tower_job_update: { node_id, tower_status,     ← Tower 作业实时状态
                      bamboo_status, progress,     含进度和 artifacts
                      artifacts }
  execution_completed: { status }                ← 执行完成

节点着色:
  pending   → 灰色边框
  running   → 黄色填充 (#fdf6ec) — Tower 作业执行中
  completed → 绿色填充 (#f0f9eb)
  failed    → 红色填充 (#fef0f0)
  skipped   → 浅灰色边框
```
