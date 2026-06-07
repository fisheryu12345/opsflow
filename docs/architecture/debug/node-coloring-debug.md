# 前端节点着色处理全过程文档

> 最后更新: 2026-06-07
> 对应 X6 版本: v3.1.7

---

## 1. 架构总览

节点着色有**两条路径**，互不冲突：

- **WebSocket 实时推送**（主路径，延迟 <500ms）— 节点状态变更时立即推送到前端，执行 `updateNodeStatus` 单节点增量着色
- **API 轮询回退**（保底路径，10s 间隔）— 全量拉取 `node_status`，执行 `loadNodeStatuses` 批量着色

```
bamboo-engine 节点状态变更
    │
    ▼
on_post_set_state 信号 (handlers.py)
    │
    ├──▶ DB 持久化 ──▶ execution.node_status JSONField
    │                    │
    │                    ├──▶ API 轮询 ──▶ 10s 间隔全量拉取着色
    │                    │
    └──▶ WebSocket 推送 ──▶ 即时推送到前端增量着色
```

---

## 2. 数据流全景图

### 2.1 后端路径

```
bamboo-engine post_set_state 信号
    │
    ▼
on_post_set_state  (signals/handlers.py:77)
    │
    ├──▶ _update_execution_node_status  (signals/state.py:18)
    │       └──  MySQL JSON_SET 原子更新 execution.node_status
    │            key = 原始 X6 节点 ID, value = 映射后的状态字符串
    │            e.g. {"node_1": "completed", "gw1": "running"}
    │
    ├──▶ _update_state_tree  (signals/state.py:68)
    │       └──  增量更新 state_tree（entered_at / exited_at / duration_ms）
    │
    ├──▶ _record_node_trace  (signals/trace.py:22)
    │       └──  创建/更新 NodeExecutionTrace 记录
    │
    ├──▶ _push_node_status_via_ws  (signals/handlers.py:32)  ← 关键: WS 推送
    │       │
    │       └── channels.group_send("user_{created_by_id}", {
    │               "type": "push.message",
    │               "json": {
    │                   "contentType": "NODE_STATUS",
    │                   "content": {
    │                       "execution_id": 42,
    │                       "node_id": "node_1",
    │                       "status": "completed"
    │                   }
    │               }
    │           })
    │
    ├──▶ (如果是 RUNNING) 更新 execution.current_node
    └──▶ (如果是 FINISHED/FAILED) _log_node_result + _write_node_trace_log
```

### 2.2 前端路径

```
MegConsumer (Django Channels)
    │
    ▼
WebSocket onmessage  (utils/websocket.ts:39)
    │
    ├── ▶ 检测 contentType === 'NODE_STATUS'
    │       └── mittBus.emit('nodeStatusChange', {execution_id, node_id, status})
    │
    └── ▶ 调用 receiveMessage(e)  ← 平台原有的消息处理（SYSTEM 通知等）
                │
                ▼
        ExecutionDetail.vue handleNodeStatusChange  (line 476)
            │  过滤 payload.execution_id === props.execution.id
            ▼
        MonitorCanvas.updateNodeStatus(nodeId, status)  (line 306)
            │
            └── applyNodeColor(nodeId, status)  — 即时着色
```

### 2.3 轮询回退路径

```
setInterval 10s  (ExecutionDetail.vue:469)
    │
    ▼
refresh()  (line 396)
    │
    ├── loadPipeline(false)  → GetExecutionDetail API
    │       │
    │       └── monitorRef.loadNodeStatuses(ex.node_status)  (MonitorCanvas.vue:286)
    │               │  batchUpdate 批量刷新
    │               └── 遍历 graph 所有节点, 调用 applyNodeColor
    │
    ├── fetchLogs()  → 刷新 Logs
    └── fetchTraces() → 刷新 Traces
```

---

## 3. 状态映射

### 3.1 bamboo-engine 原始状态 → NodeState

定义在 `backend/opsflow/core/states.py:22`

| bamboo-engine 状态 | NodeState | 前端显示 |
|---|---|---|
| `READY` | `pending` | 等待执行 |
| `RUNNING` | `running` | 执行中 |
| `FINISHED` | `completed` | 已完成 |
| `FAILED` | `failed` | 失败 |
| `SUSPENDED` | `paused` | 已暂停 |
| `REVOKED` | `cancelled` | 已取消 |
| `BLOCKED` | `blocked` | 被阻塞 |

### 3.2 颜色映射

定义在 `MonitorCanvas.vue:219` 和 `MonitorCanvas.vue:130`

| 状态 | 标签色 | 背景色 | 边框色 | 动画 |
|---|---|---|---|---|
| `pending` | `#C0C4CC` | `#FFF` | `#DCDFE6` | 无 |
| `running` | `#E6A23C` | `#FFFBF0` | `#E6A23C` | 0.6s 快速闪烁 |
| `completed` | `#67C23A` | `#F0F9EB` | `#67C23A` | 无 |
| `failed` | `#F56C6C` | `#FEF0F0` | `#F56C6C` | 无 |
| `skipped` | `#C0C4CC` | `#F5F7FA` | `#C0C4CC` | 无 |
| `pending_approval` | `#9B59B6` | `#F3E8FF` | `#9B59B6` | 无 |

---

## 4. 涉及的全部代码文件

### 4.1 后端 (Python/Django)

| 文件 | 路径 | 负责 |
|---|---|---|
| 信号处理器 | `backend/opsflow/signals/handlers.py` | 信号入口 + `_push_node_status_via_ws` WS 推送 |
| 状态管理 | `backend/opsflow/signals/state.py` | `_update_execution_node_status` DB 持久化 + 状态映射 |
| 轨迹记录 | `backend/opsflow/signals/trace.py` | `_record_node_trace` 轨迹记录 |
| 状态枚举 | `backend/opsflow/core/states.py` | `NodeState` / `PipelineState` 枚举 + 映射 + 流转矩阵 |
| 执行引擎 | `backend/opsflow/core/flow_engine.py` | `FlowEngine.run()` 构建 pipeline 并触发执行 |
| Pipeline 构建器 | `backend/opsflow/core/pipeline_builder/__init__.py` | `build_bamboo_pipeline()` 将 X6 节点树转为 bamboo 标准格式 |
| 元素创建 | `backend/opsflow/core/pipeline_builder/elements.py` | `_create_element()` 使用 X6 原始 ID 作为 bamboo Element ID |
| 执行视图 | `backend/opsflow/views/execution_views.py` | API retrieve 返回 `node_status` |
| 执行模型 | `backend/opsflow/models/execution.py` | `FlowExecution.node_status` JSONField |
| WebSocket 配置 | `backend/application/websocketConfig.py` | `MegCenter` / `DvadminWebSocket` Channels Consumer |

### 4.2 前端 (Vue/TypeScript)

| 文件 | 路径 | 负责 |
|---|---|---|
| WebSocket 工具 | `web/src/utils/websocket.ts` | WS 连接管理 + `NODE_STATUS` 自动分发到 `mittBus` |
| 执行详情页 | `web/src/views/apps/opsflow-execution/components/ExecutionDetail.vue` | 10s 轮询 + mittBus 订阅 + 调用 MonitorCanvas |
| 监控画布 | `web/src/views/apps/opsflow/components/MonitorCanvas.vue` | `applyNodeColor` + `updateNodeStatus` + `loadNodeStatuses` + 边动画 + CSS 闪烁 |
| Graph 组合式 | `web/src/views/apps/opsflow/composables/useGraphCanvas.ts` | X6 Graph 实例创建 + 缩放/居中/事件 |
| 节点形状 | `web/src/views/apps/opsflow/utils/shapes.ts` | 自定义节点注册 + 端口管理 |
| 事件类型 | `web/src/types/mitt.d.ts` | `nodeStatusChange` 事件类型定义 |
| Mitt 工具 | `web/src/utils/mitt.ts` | mitt 事件总线实例 |
| 执行 API | `web/src/api/opsflow/executions.ts` | API 调用封装 |

---

## 5. 关键代码片段详解

### 5.1 后端 WS 推送 (`handlers.py:32-64`)

```python
def _push_node_status_via_ws(execution, node_id):
    if not execution.created_by_id:
        return
    try:
        status = (execution.node_status or {}).get(node_id, '')
        if not status:
            return
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{execution.created_by_id}",          # 推送给执行创建者
                {
                    "type": "push.message",                  # MegConsumer.push_message
                    "json": {
                        "contentType": "NODE_STATUS",        # 前端根据此类型分发
                        "content": {
                            "execution_id": execution.id,
                            "node_id": node_id,
                            "status": status,
                        },
                    },
                }
            )
    except Exception:
        logger.exception(...)
```

**设计要点：**
- 使用 `user_{id}` 组推送，而非 `execution_{id}` — 已有的 `MegConsumer` 已自动将用户加入 `user_{id}` 组
- 推送给 `execution.created_by_id` — 只有执行创建者能看到实时更新
- 所有异常被捕获，不阻塞后续信号处理
- 状态从刚写入的 `execution.node_status` 内存对象中读取

### 5.2 DB 持久化 (`state.py:18-65`)

```python
def _update_execution_node_status(execution, node_id, to_state):
    node_state = map_bamboo_node_state(to_state)  # 映射: FINISHED → "completed"
    if node_state is None:
        return
    mapped = node_state.value

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE ops_flow_execution "
                "SET node_status = JSON_SET(COALESCE(node_status, '{}'), %s, CAST(%s AS JSON)) "
                "WHERE id = %s",
                [f'$."{node_id}"', mapped, execution.id]
            )
    except Exception:
        # 回退: ORM read-modify-write (非 MySQL 环境)
        execution.refresh_from_db(fields=['node_status'])
        ns = dict(execution.node_status or {})
        ns[node_id] = mapped
        execution.node_status = ns
        execution.save(update_fields=["node_status"])
        return

    # 内存同步
    ns = dict(execution.node_status or {})
    ns[node_id] = mapped
    execution.node_status = ns
```

**设计要点：**
- 使用 `JSON_SET` 原生 SQL，避免并发信号处理器之间的 read-modify-write 竞争
- `node_id` 就是原始 X6 节点 ID（如 `node_1`），因为 `elements.py` 创建元素时传入了 `id=nid`
- `CAST(%s AS JSON)` 确保存储的是 JSON 字符串类型而非带引号的文本

### 5.3 前端 WS 接收 (`websocket.ts:39-49`)

```typescript
websocket.websocket.onmessage = (e: any) => {
    // opsflow: auto-dispatch NODE_STATUS to mittBus
    try {
        const d = JSON.parse(e.data);
        if (d.contentType === 'NODE_STATUS') {
            mittBus.emit('nodeStatusChange', d.content);
        }
    } catch {}
    if (receiveMessage) {
        receiveMessage(e)  // 继续原有流程（App.vue 的 SYSTEM 通知等）
    }
}
```

**设计要点：**
- 在底层 websocket 工具中自动拦截，App.vue 完全不需要感知 `NODE_STATUS` 消息
- `mittBus.emit` 发生在 `receiveMessage` 之前，确保颜色先更新
- `catch {}` 忽略非 JSON 或非标准格式消息，不影响心跳等正常消息

### 5.4 执行详情页订阅 (`ExecutionDetail.vue:475-492`)

```typescript
// WebSocket real-time node status update handler
function handleNodeStatusChange(payload: any) {
  if (payload.execution_id === props.execution.id) {
    monitorRef.value?.updateNodeStatus?.(payload.node_id, payload.status)
  }
}

onMounted(() => {
  loadPipeline()
  fetchLogs()
  fetchTraces()
  mittBus.on('nodeStatusChange', handleNodeStatusChange)
})
onBeforeUnmount(() => {
  stopAutoRefresh()
  mittBus.off('nodeStatusChange', handleNodeStatusChange)
})
```

**设计要点：**
- 过滤 `execution_id`，防止其他执行页面的状态更新影响到当前页面
- `onMounted` 中订阅，`onBeforeUnmount` 中取消订阅，防止内存泄漏
- 使用 `?` 可选链调用，确保 MonitorCanvas 尚未初始化时不报错

### 5.5 单节点增量着色 (`MonitorCanvas.vue:306-310`)

```typescript
function updateNodeStatus(nodeId: string, status: string) {
  if (!graph.value) return
  nodeStatuses.value[nodeId] = status
  applyNodeColor(nodeId, status)
}
```

### 5.6 节点颜色应用 (`MonitorCanvas.vue:183-217`)

```typescript
const runningNodeIds = new Set<string>()

function applyNodeColor(nodeId: string, status: string) {
  if (!graph.value) return
  const cell = graph.value.getCellById(nodeId)
  if (!cell || !cell.isNode()) return

  const wasRunning = runningNodeIds.has(nodeId)
  const isRunning = status === 'running'

  if (cell.shape === 'ops-atom') {                // 主要任务卡片
    const label = cell.getData()?.label || ''
    const attrs = atomMonitorAttrs(status, label)  // 批量设置所有属性
    cell.setAttrs(attrs)
    if (isRunning) {
      cell.setAttrByPath('body/class', 'ops-node-running')   // 闪烁动画
    } else if (wasRunning) {
      cell.setAttrByPath('body/class', '')                   // 清除动画
    }
  } else {                                          // 网关、事件节点
    const color = getColor(status)
    cell.setAttrByPath('body/stroke', color)
    if (isRunning) {
      cell.setAttrByPath('body/fill', '#fdf6ec')
      cell.setAttrByPath('body/class', 'op-node-running')   // 慢速脉冲动画
    } else {
      if (wasRunning) cell.setAttrByPath('body/class', '')
      // 根据终态设置不同背景色
      if (status === 'completed') cell.setAttrByPath('body/fill', '#f0f9eb')
      else if (status === 'failed') cell.setAttrByPath('body/fill', '#fef0f0')
      else if (status === 'skipped') cell.setAttrByPath('body/fill', '#f5f7fa')
    }
  }

  if (isRunning) runningNodeIds.add(nodeId)
  else runningNodeIds.delete(nodeId)
}
```

**设计要点：**
- `runningNodeIds` Set 追踪当前 running 的节点，用于退出 running 时清除 CSS class
- `ops-atom` 节点（主要任务卡片）和 其他节点（网关/事件）分别处理
- `ops-node-running`: 0.6s 快速闪烁（`ops-blink`）
- `op-node-running`: 1.5s 慢速脉冲（`op-pulse`）

### 5.7 CSS 闪烁动画 (`MonitorCanvas.vue:395-399`)

```scss
// 非 atom 节点: 1.5s 慢脉冲
:deep(.op-node-running) {
  animation: op-pulse 1.5s ease-in-out infinite !important;
}
@keyframes op-pulse {
  0%, 100% { stroke-opacity: 1; stroke-width: 2.5; fill-opacity: 1; }
  50% { stroke-opacity: 0.3; fill-opacity: 0.5; }
}

// atom 节点: 0.6s 快速闪烁
:deep(.ops-node-running) {
  animation: ops-blink 0.6s ease-in-out infinite !important;
}
@keyframes ops-blink {
  0%, 100% { stroke-opacity: 1; stroke-width: 2.5; }
  50% { stroke-opacity: 0.2; stroke-width: 3.5; }
}
```

### 5.8 轮询批量着色 (`MonitorCanvas.vue:286-296`)

```typescript
function loadNodeStatuses(statusMap: Record<string, string>) {
  nodeStatuses.value = { ...statusMap }
  if (!graph.value) return
  // batchUpdate 合并全部颜色变更为一次 X6 渲染
  graph.value.batchUpdate('poll-color', () => {
    graph.value.getNodes().forEach((cell: any) => {
      const st = statusMap[cell.id]  // cell.id 就是原始 X6 节点 ID
      if (st) applyNodeColor(cell.id, st)
    })
  })
}
```

### 5.9 首次加载全流程 (`ExecutionDetail.vue:355-384`)

```typescript
async function loadPipeline(full = true) {
  await nextTick()
  if (!monitorRef.value) return
  try {
    const detail = await GetExecutionDetail(props.execution.id)
    const ex = detail.data?.data || detail.data || detail
    execDetail.value = ex
    monitorRef.value.setExecutionStatus?.(ex.status)

    // 首次加载: 先画图后着色
    if (full && !graphInitialized) {
      const tree = ex.pipeline_tree || ex.context?.pipeline_tree || ex.template_snapshot?.pipeline_tree
      if (tree) {
        monitorRef.value.loadGraphData(toGraphData(tree))
      } else if (ex.template) {
        const tplRes = await GetTemplateDetail(ex.template)
        const tpl = tplRes.data?.data || tplRes.data || tplRes
        if (tpl?.pipeline_tree) monitorRef.value.loadGraphData(toGraphData(tpl.pipeline_tree))
      }
      graphInitialized = true
    }

    // 画布有节点后再着色
    if (ex.node_status) {
      monitorRef.value.loadNodeStatuses?.(ex.node_status)
    }
  } catch (e) {
    console.error('[ExecutionDetail] loadPipeline error:', e)
  }
}
```

---

## 6. 节点 ID 穿透说明

### 6.1 node_N 的生成逻辑

`node_1`, `node_2` ... 的 ID **在前端生成**，当用户从 stencil 调色板拖拽节点到画布时触发。

**关键文件:** `web/src/views/apps/opsflow/composables/useDesignCanvas.ts:137-149`

```typescript
g.on('node:added', ({ node }) => {
  const oldId = node.id
  // X6 自动给新节点随机 UUID，替换为 node_N 格式
  if (oldId.length > 32 || /^node_\d+$/.test(oldId) === false) {
    setTimeout(() => {
      // 扫描画布所有节点，取最大编号 +1
      let maxN = 0
      for (const cell of g.getNodes()) {
        const m = cell.id.match(/^node_(\d+)$/)
        if (m) maxN = Math.max(maxN, parseInt(m[1], 10))
      }
      const newId = `node_${maxN + 1}`  // → node_1, node_2, ...
      // 删除旧节点（UUID），用新 ID 重建节点并重新连接边
      ...
```

**流程：**
1. 用户拖拽节点到画布 → X6 触发 `node:added`，自动给一个随机 UUID（如 `c1a2b3...`）
2. 代码检测 `oldId` 不是 `node_N` 格式 → 需要替换
3. 扫描画布已有节点，取最大的 `node_N` 编号 → 生成 `node_{maxN+1}`
4. 用 `setTimeout` 异步删除旧节点、用新 ID 重建节点并重连边

> **为什么用 setTimeout？** X6 Node 没有 `setId` 方法，无法原地修改 ID，只能通过「删除 + 重建」的方式替换。

### 6.2 穿透到 bamboo-engine

```
X6 Canvas           elements.py               build_tree()           node_status
─────────           ───────────               ────────────           ──────────
                     ServiceActivity(          activities[node_1]     {node_1:
node_1  ──► nid ──►   id="node_1"       ──►     id: "node_1"    ──►    "completed"
                       name="node_1"            name: "node_1"       }
```

**关键文件:** `backend/opsflow/core/pipeline_builder/elements.py`

每个 `_create_element` 调用都传入了 `id=nid`（即 X6 的原始 ID `node_1`），所以 bamboo-engine 的 pipeline tree 中所有节点的 key 都是 `node_1`，与 X6 cell.id 一致。

早期架构有一个冗余的 `_build_id_map` → `node_id_map` 映射层（`{node_1: node_1}` 的恒等映射），在 2026-06-07 已移除。

### 6.3 AI 生成场景的 ID

AI 生成（`create_from_ai`）和 AI 修改（`refine`）的节点 ID **直接由 LLM (DeepSeek) 生成**，遵循与前端相同的 `node_N` 命名规则。

**关键文件:** `backend/opsflow/core/llm_service.py`（`_build_system_prompt` 函数）

系统 Prompt 中包含大量 JSON 示例，所有节点 ID 都是 `node_N` 格式：

```json
{
  "nodes": [
    {"id": "node_1", "label": "Check Disk", "atom_type": "disk_check", ...},
    {"id": "node_2", "label": "Passed?", "node_type": "exclusive_gateway"},
    {"id": "node_3", "label": "Send Alert", "atom_type": "send_alert", ...}
  ],
  "edges": [
    {"from": "node_1", "to": "node_2", "label": "success"},
    {"from": "node_2", "to": "node_3", "label": "failure"}
  ]
}
```

LLM 被训练按照 `node_1`, `node_2`, `node_3`... 顺序自动编号。后端收到 AI 生成的 pipeline_tree 后直接存库，**不重写 ID**。所以无论是拖拽还是 AI 生成，所有场景下节点 ID 都是统一的 `node_N` 格式。

> 注意：`ai_layout` 端点（`backend/opsflow/views/mixins/template_ai.py:189`）只返回位置坐标（`positions: {node_id: {x, y}}`），**不修改节点 ID**。

---

## 7. 边运行动画

`MonitorCanvas.vue:314-339` — 当 `executionStatus === 'running'` 时，所有边显示虚线流动动画：

```typescript
// X6 v3 animate API，替代 v2 的 transition + recursive tick
edge.animate([
  { 'attrs/line/strokeDashoffset': 0 },
  { 'attrs/line/strokeDashoffset': -12 },
], { duration: 350, easing: 'linear', iterations: Infinity })
```

- 使用 Web Animations API 标准 `iterations: Infinity` 自动循环
- 停止时调用 `edge.getAnimations()?.forEach(a => a.cancel())`
- 动画颜色: `#E6A23C` (橙色), 虚线样式: `strokeDasharray: '8 4'`
- 非 running 状态恢复为灰色实线 `#DCDFE6`

---

## 8. 测试覆盖

### 后端测试: `backend/opsflow/tests/test_gateway_signal.py`

| 测试类 | 测试方法 | 验证内容 |
|---|---|---|
| `TestExclusiveGatewaySignalStateUpdate` | 6 tests | 节点状态写入 + 状态树更新 + 状态映射 |
| `TestExclusiveGatewaySignalHandler` | 3 tests | 信号调度 + current_node 更新 |
| `TestWsNodeStatusPush` | 3 tests | WS 推送: 跳过条件 + 正确参数 |

核心 WS 推送测试 (`TestWsNodeStatusPush`):

```python
@patch("channels.layers.get_channel_layer")
def test_push_called_with_correct_args(self, mock_get_cl):
    mock_cl = Mock()
    mock_get_cl.return_value = mock_cl

    execution = Mock()
    execution.id = 42
    execution.created_by_id = 7
    execution.node_status = {"n1": "completed"}

    _push_node_status_via_ws(execution, "n1")

    mock_cl.group_send.assert_called_once_with(
        "user_7",
        {
            "type": "push.message",
            "json": {
                "contentType": "NODE_STATUS",
                "content": {
                    "execution_id": 42,
                    "node_id": "n1",
                    "status": "completed",
                },
            },
        }
    )
```

---

## 9. 常见问题排查

### 9.1 节点颜色不更新

检查链路：

1. **后端信号是否触发** → 查看 `bamboo_engine` 日志中 `post_set_state` 信号
2. **DB 是否写入** → 查询 `ops_flow_execution` 表的 `node_status` JSONField
3. **WS 是否推送** → 查看日志中 `WS push failed` 或 `group_send` 调用
4. **前端 WS 是否连接** → 浏览器 DevTools → Network → WS 检查 `ws://` 连接状态
5. **mittBus 是否分发** → 在 `websocket.ts` 的 `mittBus.emit` 处加 console.log

### 9.2 WS 推送但前端不更新

- 检查 `created_by_id` 是否匹配当前登录用户（WS 推送到 `user_{created_by_id}` 组）
- 检查 `execution_id` 过滤：`ExecutionDetail.vue:477` 的 `payload.execution_id === props.execution.id`
- 检查 `updateNodeStatus` 中 `graph.value.getCellById(nodeId)` 是否找到对应 Cell

### 9.3 颜色闪烁一下就没了

- `onBeforeUnmount` 中调用了 `mittBus.off('nodeStatusChange')`，如果在路由切换时过早取消订阅会导致后续 WS 消息丢失
- 检查是否有多份 `ExecutionDetail` 组件实例竞争 mittBus 事件

---

## 10. 版本历史

| 日期 | 改动 |
|---|---|
| 2026-06-07 | 初始版本 — WS 实时推送 + 10s 轮询双路径 |
| 2026-06-07 | 移除冗余 `_build_id_map` 和 `node_id_map` 层，X6 ID 直接穿透 |
| 2026-06-07 | 添加 running 节点 0.6s 快速闪烁 CSS 动画 |
| 2026-06-07 | `NODE_STATUS` 分发从 App.vue 下沉到 websocket.ts |
| 2026-06-07 | X6 升级 v3.1.7，边动画改用 `animate()` API |
