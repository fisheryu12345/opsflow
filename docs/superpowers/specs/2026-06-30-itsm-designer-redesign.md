# ITSM 工单流程设计器 — 重构设计规范

> 版本: 1.0 | 日期: 2026-06-30 | 状态: 已批准

---

## 1. 概述

将 ITSM 现有的 `template/designer.vue`（自绘 SVG + drag-and-drop）替换为基于 X6 图编辑引擎的新设计器。视觉风格与 OpsFlow 一致，代码完全独立。

## 2. 文件结构

```
web/src/views/apps/itsm/
├── index.vue                          # 修改 — workflows tab 加设计按钮
├── Dashboard.vue / Delegation.vue     # 不变
└── designer/
    ├── index.vue                      # 新建 — 设计器入口
    ├── shapes.ts                      # 新建 — ITSM 专属 X6 形状
    ├── useDesigner.ts                 # 新建 — 画布初始化 + 数据转换 + 事件
    ├── DesignerToolbar.vue            # 新建 — 顶部浮动工具栏
    ├── DesignerStencil.vue            # 新建 — 左侧 stencil 面板
    ├── DesignerConfigPanel.vue        # 新建 — 右侧节点/边配置面板
    └── FieldEditorDialog.vue          # 新建 — 表单字段编辑器弹窗
```

删除 `template/designer.vue`。

## 3. 工具栏

```
┌──────────────────────────────────────────────────────────────┐
│  ← 返回    [草稿/已发布]   [流程名称输入框]                     │
│       🔍放大  🔍缩小  ⊞适应  🎯自动布局                       │
│       🤖AI生成  ✅校验  💾保存  🚀部署                        │
└──────────────────────────────────────────────────────────────┘
```

与 OpsFlow 一致的浮动样式：`bg:rgba(255,255,255,0.95)`、`border-radius:20px`、`backdrop-filter:blur(8px)`。

自动保存（防抖 2s）——节点/边/字段变更自动同步到后端 `sync` API。

## 4. 节点形状

全部注册为 `itsm-*` 前缀，不污染 opsflow 命名空间。

| 形状名 | 视觉 | 尺寸 | 对应类型 |
|--------|------|------|---------|
| `itsm-start-event` | 圆形绿底 ▶ | 56×56 | START |
| `itsm-end-event` | 圆形红底 ■ | 56×56 | END |
| `itsm-node` | 矩形卡片 208×56 | 4 端口 | NORMAL/APPROVAL/SIGN/TASK/WEBHOOK |
| `itsm-parallel-gateway` | 菱形蓝底 ⊞ | 70×70 | ROUTER_P |
| `itsm-converge-gateway` | 菱形灰底 ⨁ | 70×70 | COVERAGE |

类型 → 颜色/图标映射：
```
NORMAL    #409EFF  📝  |  APPROVAL  #E6A23C  ✓   |  SIGN  #9B59B6  ✍
TASK      #67C23A  ⚙  |  WEBHOOK   #1890FF  🔗  |  ROUTER_P/COVERAGE → 菱形
```

## 5. 边（连线）

| 边类型 | 样式 | 说明 |
|--------|------|------|
| 普通 transition | 实线 `stroke:#409EFF` | 默认连线 |
| 驳回 transition | 红色虚线 `stroke:#F56C6C` | 标签"驳回" |
| 条件 transition | 实线 `stroke:#E6A23C` | ROUTER_P 出边 |

## 6. Stencil（左面板）

X6 Stencil，7 个可拖入节点（168×48 卡片，与 ops-atom-stencil 同风格）：
填单 / 审批 / 会签 / 自动任务 / Webhook / 并行网关 / 汇聚网关

START/END 由系统自动创建。

## 7. 配置面板（右面板）

375px 宽，同 OpsFlow PropertyPanel 风格。

**节点配置：**
- NORMAL: 节点名 + 处理人类型 + 处理人 + 编辑字段
- APPROVAL: + 审批方式(单签/会签) + 编辑字段 + 允许跳过
- SIGN: + 签核方式(顺序/并行) + 编辑字段
- TASK: + api_instance_id + 入参
- WEBHOOK: + URL + 方法 + 请求头
- 网关: 仅提示

**边配置：** 标签 + 条件表达式 + 驳回标记(switch)

## 8. 字段编辑器（独立弹窗）

独立 `el-dialog`，功能：
- 字段列表（标识 + 名称 + 类型 + 必填 + 布局）
- 拖拽排序
- 添加/删除字段
- 选项编辑（SELECT/RADIO/CHECKBOX/MULTISELECT）
- 条件显示配置
- 布局选择（col-6 / col-12）
- 必填开关 + 默认值
- FILE 类型支持

**15 种字段类型完整支持：** STRING / TEXT / INT / DATE / DATETIME / SELECT / RADIO / CHECKBOX / MULTISELECT / MEMBERS / TABLE / FILE / RICHTEXT / TREESELECT / CASCADE

## 9. 数据流

```
自动保存（2s 防抖）:
  POST /api/itsm/states/sync/     — 全量同步节点
  POST /api/itsm/transitions/sync/  — 全量同步连线
  POST /api/itsm/fields/batch_update/  — 批量保存字段

部署:
  POST /api/itsm/workflows/{id}/deploy/  → WorkflowVersion 快照

文件上传:
  POST /api/itsm/tickets/{id}/upload-file/  → 工单附件

加载:
  GET /api/itsm/workflows/{id}/
  GET /api/itsm/states/?workflow={id}
  GET /api/itsm/transitions/?workflow={id}
  GET /api/itsm/fields/?state__workflow={id}
```

## 10. 校验规则

1. ✅ 必须有 START 和 END
2. ✅ 所有节点必须从 START 可达
3. ✅ 所有节点必须可达 END
4. ✅ APPROVAL 节点必须配置处理人
5. ✅ ROUTER_P 出边必须有 condition
6. ✅ ROUTER_P / COVERAGE 数量匹配
7. ✅ 无孤立节点
8. ✅ 节点名称非空

## 11. 后端 API 变更

| 端点 | 说明 |
|------|------|
| `POST /api/itsm/states/batch_update/` | 批量创建/更新节点 |
| `POST /api/itsm/states/sync/` | 全量同步节点（差异删除） |
| `POST /api/itsm/transitions/batch_update/` | 批量创建/更新连线 |
| `POST /api/itsm/transitions/sync/` | 全量同步连线（差异删除） |
| `POST /api/itsm/fields/batch_update/` | 批量创建/更新字段 |
| `POST /api/itsm/tickets/{id}/upload-file/` | 工单文件上传 |

## 12. 文件清单

### 新建（6 前端文件）

| 文件 | 说明 |
|------|------|
| `designer/index.vue` | 设计器入口 |
| `designer/shapes.ts` | ITSM 专属 X6 形状 |
| `designer/useDesigner.ts` | 画布 composable |
| `designer/DesignerToolbar.vue` | 顶部工具栏 |
| `designer/DesignerStencil.vue` | 左侧 stencil |
| `designer/DesignerConfigPanel.vue` | 右侧配置面板 |
| `designer/FieldEditorDialog.vue` | 字段编辑器弹窗 |

### 修改（1 前端 + 2 后端）

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/itsm/index.vue` | workflows tab 加设计按钮 |
| `backend/itsm/views/workflow_views.py` | 新增 batch_update + sync 端点 |
| `backend/itsm/views/ticket_views.py` | 新增 upload_file 端点 |

### 删除

| 文件 | 说明 |
|------|------|
| `web/src/views/apps/itsm/template/designer.vue` | 旧设计器 |
