# X6 只读流程图 — 工单详情流程步骤可视化

## Context

当前工单详情页（`TicketDetail.vue`）的"流程步骤"使用 el-steps 水平条展示节点，无法表达并行网关、条件分支、驳回循环等复杂拓扑。审批人/处理人无法直观理解工单的整体流转路径。

## 设计

### 替换方式

将 `TicketDetail.vue` 中的"流程步骤" el-steps 替换为一个 **只读 X6 流程图组件** `FlowChart.vue`。

### 组件定位

`web/src/views/apps/itsm/FlowChart.vue` — 只读流程图展示组件

**Props:**
- `states: Record<string, any>` — workflowVersion.states（所有节点定义）
- `transitions: any[]` — workflowVersion.transitions（所有连线）
- `nodeStatus: Array<{state_id: number, status: string}>` — 每个节点的运行时状态

**内部逻辑：**
- 创建 X6 Graph，禁用所有编辑功能（无 connecting、无 stencil、无 keyboard）
- 启用 panning（可拖拽平移）+ mousewheel 缩放
- 根据 states + transitions 渲染节点和连线
- 根据 nodeStatus 设置节点状态颜色

### 节点视觉

| 状态 | 配色 | 说明 |
|------|------|------|
| FINISHED | 绿色边框/图标（#67C23A）| 已完成 |
| RUNNING | 蓝色边框 + 脉动动画（#409EFF）| 当前节点 |
| WAIT | 灰色（#C0C4CC）| 未到达 |

节点形状复用 designer 的 `shapes.ts` 中的 `itsm-node` 定义（含类型标签色块）。

### 布局

使用项目已有的后端布局引擎：`POST /api/itsm/workflows/{id}/layout/` 计算节点坐标。
（`useDesigner.ts` 中已有 `autoLayout` 函数调用此接口）

或者使用 X6 内置的 `dagre` 布局（X6 自带 `Graph.layout('dagre')`），简单流程可直接前端布局。

### 定位

替换 `TicketDetail.vue` 中的流程步骤区块：

```
[Header]
[申请内容]
[流程图 FlowChart]    ← 替代 el-steps
[当前节点 · 审批]
[已完成节点 Timeline]
```

## 改动范围

### 新文件
- `web/src/views/apps/itsm/FlowChart.vue` — 只读 X6 流程图组件

### 修改文件
- `web/src/views/apps/itsm/TicketDetail.vue`
  - import FlowChart
  - 替换流程步骤模板
  - 传入 states / transitions / nodeStatus

### 布局数据流

```
FlowChart.vue
  │ props: states, transitions, nodeStatus
  │
  ├─ onMounted → 构建 X6 Graph
  ├─ watch states+transitions
  │     │
  │     ├─ 遍历 transitions 确定节点连接关系
  │     ├─ 使用 dagre 布局计算坐标（或后端 layout API）
  │     ├─ 渲染节点（含状态着色）
  │     └─ 渲染连线（含驳回线着色）
  │
  └─ watch nodeStatus
        └─ 更新节点颜色 + 脉动动画
```

## 不涉及
- 后端无改动
- 路由无改动
- 无新依赖（X6 已安装）
