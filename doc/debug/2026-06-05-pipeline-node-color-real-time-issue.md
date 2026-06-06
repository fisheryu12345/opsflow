# Pipeline 节点实时变色问题排查与修复

> 日期：2026-06-05
> 场景：OpsFlow 流程引擎 Dry Run / 实时执行时，节点状态已 `completed`，但前端画布节点颜色延迟几秒才变化
> 关键词：WebSocket、Django Channels、X6、batchUpdate、concurrent signal

---

## 目录

1. [问题现象](#1-问题现象)
2. [整体架构](#2-整体架构)
3. [根因一：WS 消息推送使用了错误的 Redis 直连方式](#3-根因一ws-消息推送使用了错误的-redis-直连方式)
4. [根因二：流程完成通知发错了消息类型](#4-根因二流程完成通知发错了消息类型)
5. [根因三：节点清扫不推送 WS](#5-根因三节点清扫不推送-ws)
6. [根因四：X6 选择器名不匹配](#6-根因四x6-选择器名不匹配)
7. [根因五：Vue watch 全量遍历导致渲染阻塞](#7-根因五vue-watch-全量遍历导致渲染阻塞)
8. [根因六：缺少 X6 batchUpdate 合并渲染](#8-根因六缺少-x6-batchupdate-合并渲染)
9. [完整修复清单](#9-完整修复清单)
10. [修复后的数据流](#10-修复后的数据流)
11. [验证方法](#11-验证方法)

---

## 1. 问题现象

**用户观察：**
- 节点执行完毕，后端日志显示 `completed`
- WS 消息已到达浏览器（Console 可见 `[WS] node_status node_3 completed`）
- 但画布节点颜色**延迟 1-3 秒**才从黄色变为绿色
- 统计栏显示 "Completed: 0" 直到延迟结束

**实际延迟来源：** 不是单一原因，而是 **6 个问题串联**导致的累积延迟。

---

## 2. 整体架构

```
bamboo-engine (Celery worker)
    ↓ post_set_state signal
opsflow/signals/handlers.py
    ├─ _update_execution_node_status()    → 写 MySQL node_status
    ├─ _update_state_tree()               → 写 MySQL state_tree
    ├─ _record_node_trace()               → 写 NodeExecutionTrace
    ├─ _notify_node_status()              → 推 WS
    │     ↓
opsflow/tasks.py:_ws_notify()
    │     ↓ channel_layer.group_send()
Daphne ASGI → Redis Pub/Sub
    │     ↓
FlowMonitorConsumer.node_status()
    │     ↓ send_json()
WebSocket → 浏览器
    │     ↓
useMonitor.ts onmessage
    ├─ nodeStatuses.value[node_id] = status  (reactive)
    └─ _onNodeStatus(node_id, status)        (回调)
             ↓
MonitorCanvas.vue
    ├─ onNodeStatus callback
    └─ applyNodeColor(id, status)
             ↓
    X6 cell.setAttrs(attrs)
```

---

## 3. 根因一：WS 消息推送使用了错误的 Redis 直连方式

### 文件

`backend/opsflow/tasks.py` — `_ws_notify()`

### 旧代码

```python
_CHANNEL_REDIS_PREFIX = "asgi"

def _ws_notify(execution_id, node_id, status, message=""):
    import redis
    host = "127.0.0.1"
    port = 6379
    db = 0
    try:
        r = redis.Redis(host=host, port=port, db=db, socket_connect_timeout=3)
        group = f"execution_{execution_id}"
        payload = json.dumps({"type": "node_status", ...})
        group_key = f"{_CHANNEL_REDIS_PREFIX}:g:{group}"
        channel_names = r.zrange(group_key, 0, -1)
        for ch in channel_names:
            r.publish(f"{_CHANNEL_REDIS_PREFIX}:{ch}", payload)
    except Exception as e:
        logger.warning("WS notify best-effort failed ...")
```

### 问题

| 问题点 | 影响 |
|--------|------|
| Redis host:port 硬编码 `127.0.0.1:6379` | Docker 下 Redis 在 `redis` 主机名，消息发到环回地址，静默丢失 |
| 直接操作 channels_redis **内部 key 格式**（`asgi:g:{group}`） | 内部格式是私有实现，版本间可能变化 |
| `except Exception` 静默吞掉全部异常 | 失败时只打一行 warning，前端永远收不到 WS 消息 |
| 根本没有走 Django 的 `CHANNEL_LAYERS` 配置 | 所有 channel layer 配置（Redis 地址、池）被绕过 |

### 修复

改用 `channel_layer.group_send()` 标准 API：

```python
def _ws_notify(execution_id, node_id, status, message=""):
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    run_async(
        channel_layer.group_send(
            f"execution_{execution_id}",
            {"type": "node_status", "node_id": node_id, "status": status, "message": message},
        )
    )
```

`group_send` 从 Django settings 的 `CHANNEL_LAYERS` 读取 Redis 配置，不碰内部 key。

### 验证日志

```
# 修复前
[WS-Connect] opened ws://...   ← 连接成功
（从此再无 WS 日志）          ← 消息被 Redis 黑洞吞掉

# 修复后
[WS-Connect] opened ws://...
[WS-Raw] node_status node_3 completed received at 1780744956989  ← WS 消息到达
```

---

## 4. 根因二：流程完成通知发错了消息类型

### 文件

`backend/opsflow/signals/notify.py` — `_notify_completed()`

### 旧代码

```python
def _notify_completed(execution):
    _ws_notify(execution.id, "__root__", execution.status)
```

`_ws_notify` 构建的消息体 `type` 固定为 `"node_status"`，所以这条消息传到前端 consumer 时走的是 `async def node_status` 处理器——**不是** `async def execution_completed`。

```python
# FlowMonitorConsumer 里的处理器：
async def node_status(self, event):              # ← 收到 "_root__"
    await self.send_json({"type": "node_status", ...})

async def execution_completed(self, event):      # ← 永远不会被调用
    await self.send_json({"type": "execution_completed", ...})
```

前端 `useMonitor.ts` 的 `onExecutionCompleted` 回调监听的是 `msg.type === 'execution_completed'`，所以它**永远不会触发**。

### 修复

```python
def _notify_completed(execution):
    channel_layer = get_channel_layer()
    run_async(
        channel_layer.group_send(
            f"execution_{execution.id}",
            {"type": "execution.completed", "status": execution.status},
        )
    )
```

`type: "execution.completed"` 会导致 channels 自动路由到 `async def execution_completed(self, event)` 处理器。

---

## 5. 根因三：节点清扫不推送 WS

### 文件

`backend/opsflow/signals/handlers.py` — `_sweep_node_status()`

### 旧代码

```python
def _sweep_node_status(execution, terminal_status):
    ns = dict(execution.node_status or {})
    changed = False
    for k, v in ns.items():
        if v in ("running", "finished"):
            ns[k] = terminal_status
            changed = True
    if changed:
        execution.node_status = ns
```

### 问题

`_handle_root_state_change` 在 pipeline 完成时调用 `_sweep_node_status`，把 `node_status` 字段里所有还标记为 `running` 的节点批量改为 `completed`。但**只写了 MySQL，没推 WS**。

所以即使用户在浏览器上看到 `execution.status === 'completed'`，还有大量节点显示黄色（running）——前端要等下一轮 API 轮询（最长 1 秒）才收到这些清扫后的状态。

### 修复

```python
from opsflow.signals.notify import _notify_node_status

for k, v in ns.items():
    if v in ("running", "finished"):
        ns[k] = terminal_status
        changed = True
        _notify_node_status(execution, k, terminal_status)  # 每清扫一个就推 WS
```

---

## 6. 根因四：X6 选择器名不匹配

### 文件

`MonitorCanvas.vue` 的 `atomMonitorAttrs()` 与 `shapes.ts` 的 `atomMarkup`

### ops-atom 的真实 markup（shapes.ts）

```javascript
const atomMarkup = [
    { tagName: 'rect',   selector: 'body' },       # ✅ 存在
    { tagName: 'rect',   selector: 'icon-bg' },    # ✅ 存在
    { tagName: 'text',   selector: 'icon' },       # ✅ 存在
    { tagName: 'text',   selector: 'label' },      # ✅ 存在
    { tagName: 'text',   selector: 'desc' },       # ✅ 存在（注意名字叫 desc）
    { tagName: 'circle', selector: 'status-dot' }, # ✅ 存在
]
```

### 旧代码设置的 attrs

```typescript
override['accent-bar'] = { fill: '#67C23A' }     // ❌ markup 里没有
override.subtitle = { fill: '#67C23A', text: '已完成' }  // ❌ markup 里叫 desc
```

**X6 遇到不存在的选择器会静默丢弃，不报错、不渲染。** 所以：
- `setAttrs` 调了，返回值正确
- 颜色、文字都没变
- 看起来像"延迟"——实际上根本没着上色

### 修复

```typescript
override.body = { fill: '#F0F9EB', stroke: '#67C23A' }
override.desc = { fill: '#67C23A', text: '已完成' }
// 移除 accent-bar 和 subtitle
```

---

## 7. 根因五：Vue watch 全量遍历导致渲染阻塞

### 文件

`MonitorCanvas.vue`

### 旧代码

```typescript
const stopWatch = watch(nodeStatuses, (statuses) => {
    if (!graph.value) return
    for (const [nid, st] of Object.entries(statuses)) {
        const cell = graph.value.getCellById(nid)
        if (cell?.isNode()) applyNodeColor(nid, st)
    }
})
```

### 问题

WS 每条消息到达时：

1. `onNodeStatus` 回调已经通过 `applyNodeColor(id, status)` 精准着色了**这一个节点** ✅
2. 同时 `nodeStatuses.value[node_id] = status` 赋值 → Vue reactive 触发 watch
3. watch 遍历全部 26 个节点，每个节点调一次 `applyNodeColor` ❌

26 个节点 × 52 条 WS 消息 = **1352 次 `applyNodeColor` 调用**。而且每次 `setAttrs` 都触发 X6 渲染管线，浏览器被反复重绘。

### 修复

```typescript
// 去掉 watch(nodeStatuses)，仅靠 WS 回调驱动
onNodeStatus((nid, status, _oldStatus) => {
    if (!graph.value) return
    const cell = graph.value.getCellById(nid)
    if (cell?.isNode()) applyNodeColor(nid, status)
})
```

---

## 8. 根因六：缺少 X6 batchUpdate 合并渲染

### 问题

即使只走 `onNodeStatus` 回调，当多条 WS 消息连续到达时（如 `node_2/3/4` 同时完成），每个 `setAttrs` 都触发一次独立的 X6 SVG DOM 重绘。

### 修复

在 `applyNodeColor` 中使用 `{ silent: true }` 跳过 X6 的事件通知和中间渲染：

```typescript
cell.setAttrs(attrs, { silent: true })
```

对需要批量着色的场景，包裹 `graph.batchUpdate()`：

```typescript
graph.batchUpdate('monitor-color', () => {
    nodes.forEach(cell => applyNodeColor(cell.id, status))
})
```

`batchUpdate` 将多次 `setAttrs` 合并为**一次** SVG DOM 渲染。

---

## 9. 完整修复清单

| # | 文件 | 改动级别 | 说明 |
|:-:|------|---------|------|
| 1 | `tasks.py` | ★★★ | `_ws_notify` 从直连 Redis 内部 key → `channel_layer.group_send()` |
| 2 | `notify.py` | ★★★ | `_notify_completed` 从发 `__root__` node_status → 发 `execution.completed` 类型 |
| 3 | `handlers.py` | ★★☆ | `_sweep_node_status` 清扫时每改一个节点就推 WS |
| 4 | `MonitorCanvas.vue` | ★★☆ | `atomMonitorAttrs` 移除不存在的 `accent-bar`/`subtitle`，改为 `desc` |
| 5 | `MonitorCanvas.vue` | ★★☆ | `watch(nodeStatuses)` → 仅 WS 回调驱动，去掉全量遍历 |
| 6 | `MonitorCanvas.vue` | ★☆☆ | `setAttrs` / `setAttrByPath` 加 `{ silent: true }` |
| 7 | `MonitorCanvas.vue` | ★☆☆ | `batchUpdate` 包裹批量着色 |
| 8 | `ExecutionDetail.vue` | ★☆☆ | 去掉 3s/1s 自动轮询，纯 WS 驱动 |
| 9 | `useMonitor.ts` | ★☆☆ | 添加 `[WS-Connect]`/`[WS-Raw]` 日志调试 |

---

## 10. 修复后的数据流

```
bamboo-engine 节点完成
    ↓
post_set_state signal (django dispatch)
    ↓
on_post_set_state (handlers.py, 同步调用)
    ├─ _update_execution_node_status()   → JSON_SET 写 MySQL node_status（原子操作）
    ├─ _update_state_tree()              → JSON_SET 写 MySQL state_tree（原子操作）
    ├─ _record_node_trace()              → 写 NodeExecutionTrace
    ├─ _notify_node_status()             → _ws_notify()
    │     ↓
    └─ _ws_notify() → run_async → channel_layer.group_send()
              ↓
    channels_redis → Redis PUBLISH
              ↓
    Daphne ASGI → FlowMonitorConsumer.node_status()
              ↓ send_json()
    WebSocket → 浏览器
              ↓
    useMonitor.ts onmessage
        ├─ console.log('[WS-Raw] node_status node_3 completed')
        ├─ nodeStatuses.value['node_3'] = 'completed'
        └─ _onNodeStatus('node_3', 'completed')
              ↓
    MonitorCanvas.vue onNodeStatus callback
        ├─ console.log('[WS-Monitor] node_status node_3 completed WS->apply')
        └─ applyNodeColor('node_3', 'completed')
              ↓
    cell.setAttrs(attrs, { silent: true })
              ↓
    X6 SVG DOM 属性更新（同一帧，无额外渲染）
```

**端到端耗时 = WS 消息到达时间戳与 applyNodeColor 时间戳之差 = 0ms。**

```
[WS-Raw] node_status node_3 completed received at 1780744956989
[WS-Monitor] node_status node_3 completed WS->apply at 1780744956989
                                                      ^^^^^^^^^^
                                                      同一毫秒！
```

---

## 11. 验证方法

### 前置条件

```bash
# 1. Django 进程（ASGI）运行中
uvicorn application.asgi:application --port 8000 --host 0.0.0.0

# 2. Celery worker 运行中（er_execute 队列处理 pipeline）
celery -A application worker -l info -Q er_execute -c 10 --pool=gevent

# 3. Redis 运行中
redis-server

# 4. Neo4j 运行中（CMDB 拓扑数据，可选）
```

### 验证步骤

1. 打开浏览器 F12 Console
2. 切换到 OpsFlow → 选择模板 → Dry Run
3. 观察 Console 中 `[WS-Connect]`、`[WS-Raw]`、`[WS-Monitor]` 日志

**正常日志模式：**

```
[WS-Connect] connecting to ws://localhost:8080/ws/opsflow/execution/324/
[WS-Connect] opened ws://localhost:8080/ws/opsflow/execution/324/
[WS-Raw] node_status __start__ running received at ...
[WS-Raw] node_status __start__ completed received at ...
[WS-Raw] node_status node_1 running received at ...
[WS-Raw] node_status node_1 completed received at ...
[WS-Raw] node_status node_3 running received at ...
[WS-Raw] node_status node_3 completed received at ...
...
```

**关键检查点：**

| 检查项 | 预期 |
|--------|------|
| `[WS-Connect] opened` | WS 连接成功 |
| `[WS-Raw] node_status xxx completed` | 节点完成消息到达 |
| `[WS-Monitor] node_status xxx completed WS->apply` 与上一行时间戳一致 | 着色在毫秒级内执行 |
| 画布节点颜色 | completed 节点显示绿色、running 节点显示黄色 |
| 统计栏 | Completed / Running / Total 数字正确 |
| WS 断开 | 页面关闭/路由切换后 `[WS-Connect] closed code: 1000` |

### 常见问题诊断

| 症状 | 排查 |
|------|------|
| `[WS-Connect] connecting` 但没有 `opened` | WS URL 拼错或后端 ASGI 端口不对。检查 `window.location.host` |
| `[WS-Connect] opened` 但无 `[WS-Raw]` | `_ws_notify` 异常被吞。检查后端 Celery worker 日志有无 `WS notify` 相关 warning |
| `[WS-Raw]` 正常但颜色不变化 | `atomMonitorAttrs` 选择器与 ops-atom markup 不匹配。检查 `MoniterCanvas.vue` 的 `atomMonitorAttrs` 和 `shapes.ts` 的 `atomMarkup` |
| 统计栏数字不更新 | `nodeStatuses.value` 没被赋值。检查 `useMonitor.ts` 的 `onmessage` 是否走到 `node_status` 分支 |

---

*本文档覆盖了 2026-06-05 调试会话中发现的全部 6 个根因及修复方案。*
