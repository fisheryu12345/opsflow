# AI 辅助 DR 拓扑布局设计 / AI-Assisted DR Topology Layout

> 创建日期: 2026-06-12
> 状态: 设计草案
> 涉及 App: opsflow, cmdb

---

## 1. 概述

当前 DR 拓扑图使用手算两列布局（主站/备站纵向排列），节点位置固定，无法自适应复杂拓扑变化。本设计引入 AI 计算节点位置，替代手工布局逻辑。

### 核心流程

```
用户点击「AI 布局」
  → 前端发送 nodes/edges 到后端
  → 后端调用 LLM + 布局规则 → 返回坐标数组
  → 前端更新 G6 节点位置
```

---

## 2. 后端 API

复用 `POST /api/opsflow/templates/ai_layout/` 已有端点，新增 `mode='dr_topology'` 参数。

### 请求

```json
{
  "mode": "dr_topology",
  "nodes": [
    {"id": "fa8f1220...", "type": "DrSite", "label": "主站-北京"},
    {"id": "host-app-01", "type": "Host", "label": "应用服务器-01"},
    {"id": "3001-uuid", "type": "Process", "label": "order-service"}
  ],
  "edges": [
    {"from": "fa8f1220...", "to": "host-app-01", "type": "SITE_CONTAINS"},
    {"from": "3001-uuid", "to": "host-app-01", "type": "RUNS_ON"}
  ]
}
```

### 响应

```json
{
  "data": {
    "positions": [
      {"id": "fa8f1220...", "x": 100, "y": 80},
      {"id": "host-app-01", "x": 100, "y": 180},
      {"id": "3001-uuid", "x": 100, "y": 260}
    ]
  }
}
```

### 实现位置

`backend/opsflow/views/mixins/template_ai.py` — `TemplateAIMixin` 增加 `_ai_dr_layout()` 方法。

---

## 3. AI Prompt

```python
DR_LAYOUT_SYSTEM_PROMPT = """你是一个拓扑图布局专家。请根据给定的 DR 拓扑数据，计算每个节点的最佳位置 (x, y)。

布局原则：
1. 主站 DrSite 放在左侧，备站 DrSite 放在右侧
2. 每个 DrSite 下的 Host 放在该站点下方，按名称纵向排列
3. 每个 Host 下的 Process 放在该 Host 下方缩进
4. FAILOVER_TO 关系的两端（主站→备站）在水平方向对齐
5. 节点间距：同级别至少 60px，上下级至少 80px，站点间至少 300px
6. 避免节点重叠

输出 JSON 格式（必须，严格遵循）：
{
  "positions": [
    {"id": "节点ID", "x": 整数坐标, "y": 整数坐标}
  ]
}

只输出 JSON，不要其他文字。
"""
```

**temperature: 0.1**（低随机性，位置计算要精确）

---

## 4. 前端集成

### 按钮位置

在 `DrTopologyCanvas.vue` 的工具栏 `dtp-bar` 中，Refresh 按钮旁边：

```html
<el-button size="small" type="primary" :loading="aiLayouting" @click="doAiLayout">
  <el-icon><MagicStick /></el-icon> AI 布局
</el-button>
```

### 处理逻辑

```typescript
async function doAiLayout() {
  aiLayouting.value = true
  try {
    const { request } = await import('/@/utils/service')
    const res = await request({
      url: '/api/opsflow/templates/ai_layout/',
      method: 'post',
      data: {
        mode: 'dr_topology',
        nodes: props.nodes.map(n => ({ id: n.id, type: mc(n), label: nlabel(n) })),
        edges: props.edges.map(e => ({ from: e.from || e.source, to: e.to || e.target, type: e.type })),
      },
    })
    const positions = res?.data?.data?.positions || res?.data?.positions || []
    if (!positions.length) return
    for (const pos of positions) {
      const item = graph.value?.findById(pos.id)
      if (item) graph.value?.updateItem(item, { x: pos.x, y: pos.y })
    }
    graph.value?.fitView([40, 40, 40, 40])
  } finally {
    aiLayouting.value = false
  }
}
```

---

## 5. 文件修改

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/opsflow/views/mixins/template_ai.py` | **修改** | `ai_layout` 新增 `mode='dr_topology'` 分支，调用 `_ai_dr_layout()` |
| `web/src/views/apps/cmdb/components/DrTopologyCanvas.vue` | **修改** | 工具栏新增「AI 布局」按钮 + `doAiLayout()` |

**不改其他文件**。复用现有 API 端点，不新增路由。

---

## 6. 未纳入范围

- ❌ AI 坐标持久化缓存
- ❌ 拖拽后重新布局
- ❌ 多轮 AI 布局优化
