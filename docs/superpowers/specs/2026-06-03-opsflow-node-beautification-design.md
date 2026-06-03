# Opsflow 原子节点美化设计方案

## 概述

对 Opsflow 流程编辑器的原子节点（ops-atom）进行视觉升级，基于 X6 的 SVG markup 能力，实现卡片化精致外观 + 运行时状态反馈。同时统一美化 Start/End 事件节点、网关节点和子流程节点。

## 动机

当前 ops-atom 节点就是一个 180×48 的白色圆角矩形 + 居中文字标签，没有任何图标、装饰或运行状态反馈。这使得：
- 设计态下无法快速区分不同插件类型
- 运行态下状态表达有限（仅有边框变色 + pulse）
- 视觉品质与 X6 的 SVG 能力不匹配

## 设计目标

| 维度 | 目标 |
|------|------|
| 外观 | 卡片化设计，阴影/渐变/左色条/类型图标，提升精致感 |
| 类型区分 | 不同插件分组用不同颜色和图标，一眼可识别 |
| 运行反馈 | 执行状态（进行中/成功/失败）有丰富的颜色/文字/动画变化 |
| 可扩展 | 新插件类型只需后端配置 icon+color，前端自动适配 |

## 设计细节

### 节点尺寸

220×60 — 相比当前的 180×48 增大，容纳图标 + 标题 + 副标题两行信息。

### 设计态节点结构

```
┌──────────────────────────────────┐
│▌ ┌──┐ 标题文字                   ●│  ← 风险等级圆点
│▌ │🔗│ 副标题（分组 · 风险）       │
│▌ └──┘                             │
└──────────────────────────────────┘
 ↑      ↑         ↑             ↑
左色条  图标      title        status-dot
(4px)  (28x28)   subtitle     (右上角)
```

SVG markup 层级（X6 `markup` 数组）：
1. `shadow` — 阴影偏移矩形（增加立体感）
2. `accent-bar` — 左侧 4px 色条，表示插件分组颜色
3. `body` — 白色主卡片体，圆角 8px
4. `icon-bg` — 图标背景圆（28px），带浅色填充
5. `icon` — 图标文字（使用 Element Plus / Unicode 图标）
6. `label` — 主标题（13px 加粗，#303133）
7. `subtitle` — 副标题（11px，#909399）
8. `status-dot` — 右上角风险等级圆点（设计态隐藏或低透明度）

### Port 交互增强

| 状态 | 表现 |
|------|------|
| 默认 | r=3, opacity=0.2（比目前的 0.35 更弱，减少视觉干扰） |
| 节点 hover | r=5, opacity=1, strokeWidth=2（保持现有行为） |
| 连接拖拽中（目标） | r=7, 浅蓝填充 + 脉动光环动画（新增） |

### 运行态状态映射

| 状态 | 左色条 | body 描边 | body 填充 | 文字 | 图标效果 | 副标题 |
|------|--------|----------|----------|------|---------|--------|
| pending | #909399 | #DCDFE6 | #FFF | #C0C4CC | 灰显 | 等待执行 |
| running | #E6A23C | #E6A23C | #FFFBF0 | #E6A23C | 旋转进度环 | 执行中 |
| completed | #67C23A | #67C23A | #F0F9EB | #67C23A | 绿色对勾 | 已完成 |
| failed | #F56C6C | #F56C6C | #FEF0F0 | #F56C6C | 红色叉号 | 失败 |
| skipped | #C0C4CC | #C0C4CC | #F5F7FA | #C0C4CC | 灰显跳过 | 已跳过 |
| pending_approval | #9B59B6 | #9B59B6 | #F3E8FF | #9B59B6 | 锁图标 | 等待审批 |

设计态只需切换 `accent-bar` 颜色 + 图标背景色，body 保持白色。

副标题在运行态显示纯状态文字（如"已完成"、"执行中"、"失败"），不显示耗时/错误详情。

### 动画效果

- **running 脉动** — 图标背景环形 dasharray 旋转动画（1.2s infinite）
- **节点 hover** — body 轻微上移 + 阴影加深（通过 CSS transform）
- **running 状态** — 右上角状态点 opacity pulse（1.5s infinite）
- **端口 hover** — 保持现有 0.2s transition

## 插件分组 → 颜色 + 图标 映射

后端 PluginMeta 模型扩展 `icon` 和 `color` 字段，前端自动读取渲染。

| 分组 | 主题色 | 图标概念 |
|------|--------|---------|
| 通用工具 | #409EFF | 🔧 |
| HTTP | #67C23A | 🔗 |
| Ansible | #E6A23C | 🖥️ |
| Monitor | #F56C6C | 📊 |
| ESXi | #9B59B6 | 💻 |
| Redfish | #00BCD4 | 🔌 |
| ServiceNow | #FF9800 | 🎫 |
| NetApp | #607D8B | 💾 |
| Pmax | #795548 | 📈 |

未知分组回退到 #409EFF + ❓。

## 影响范围

### 文件修改

| 文件 | 改动 |
|------|------|
| `backend/opsflow/plugins/base.py` | BasePlugin 增加 icon/color 类属性 |
| `backend/opsflow/models/plugin.py` | PluginMeta 增加 icon/color 字段 |
| `backend/opsflow/plugins/registry.py` | sync 时同步 icon/color |
| `web/src/views/apps/opsflow/utils/shapes.ts` | ops-atom 重写为卡片式 markup；其他节点统一阴影/交互 |
| `web/src/views/apps/opsflow/composables/useDesignCanvas.ts` | 端口交互增强（拖拽脉动） |
| `web/src/views/apps/opsflow/composables/useMonitor.ts` | 更新状态颜色映射 |
| `web/src/views/apps/opsflow/components/MonitorCanvas.vue` | 适配新节点 markup 的状态切换 |
| `web/src/views/apps/opsflow/styles/` | 新增节点动画 CSS |

### 不完全影响

- 审批节点（ops-approval）保持现有菱形样式，不做卡片化
- 节点的数据模型不变（不涉及 backend 的 pipeline schema 更改）
- 运行态端口在 MonitorCanvas 中隐藏（runmode 不可编辑）
- 状态文字不显示耗时/错误详情

## 未纳入范围

- 审批节点形状改造（后续单独处理）
- 节点上下文菜单或节点内表单
- 节点内嵌进度条或数据预览
- 深色模式支持
