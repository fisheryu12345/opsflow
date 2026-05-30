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
│   │   ├── Diff
│   │   ├── AI Analyze
│   │   ├── New Template
│   │   └── Save
│   ├── Stencil 组件面板 (左侧, 可折叠)
│   │   ├── Check 组 (3)
│   │   ├── Action 组 (8)
│   │   ├── Control 组 (2)
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

```
┌─ Components ───────┐
│ 🔍 Search...       │
│                    │
│ ▼ Check            │
│  ┌───┐ ┌───┐     │
│  │Disk│ │Ping│     │
│  └───┘ └───┘     │
│  ┌───┐           │
│  │Hlth│           │
│  └───┘           │
│                    │
│ ▼ Action           │
│  ┌───┐ ┌───┐     │
│  │Shl │ │Upl │     │
│  └───┘ └───┘     │
│  ┌───┐ ┌───┐     │
│  │Cpy │ │Scr │     │
│  └───┘ └───┘     │
│  ┌───┐ ┌───┐     │
│  │Bak │ │Deploy  │
│  └───┘ └───┘     │
│  ┌───┐ ┌───┐     │
│  │Dckr│ │Nginx│   │
│  └───┘ └───┘     │
│                    │
│ ▼ Control          │
│  ┌───┐ ┌───┐     │
│  │Srv │ │Alert│   │
│  └───┘ └───┘     │
│                    │
│ ▼ Gateway/Event    │
│  Start  End       │
│  Cond?  Parallel  │
│  C.Par. Converge  │
└────────────────────┘
```

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
