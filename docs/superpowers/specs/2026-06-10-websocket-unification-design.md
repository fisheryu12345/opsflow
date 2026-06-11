# OPSflow WebSocket 统一规范设计

> **日期:** 2026-06-10
> **状态:** 设计已批准

---

## 1. 问题陈述

### 1.1 当前痛点

| # | 问题 | 表现 |
|---|------|------|
| 1 | **推送入口分散** | 后端 5 个点各自独立获取 channel_layer、try-catch、async_to_sync，代码重复 |
| 2 | **消息格式不统一** | `contentType: "SYSTEM"`、`type: "tower_job_update"`、`type: "execution.completed"` 同时存在 |
| 3 | **`execution_{id}` 组消息丢失** | Tower 进度和 FlowEngine 完成推送到 `execution_{id}` 组，但前端只加入了 `user_{id}` 组 |
| 4 | **前端心跳频繁** | 2s 间隔，Daphne 自带 ping/pong 保活，浪费带宽 |
| 5 | **前端类型缺失** | `socket` 类型文件不存在，靠 `@ts-ignore` 压制 |
| 6 | **mittBus 桥接不必要** | WebSocket → mittBus → ExecutionDetail，增加中间层 |
| 7 | **Consumer 死逻辑** | `MegCenter.receive()` 处理 `message_id`，但前端从未发送 |

### 1.2 设计目标

- **统一消息信封** — 前后端确认一套标准消息格式
- **统一推送入口** — 后端一个模块负责所有 WS 推送
- **修复执行通知** — 废除 `execution_{id}` 组，合并到 `user_{id}` 组
- **前端类型安全** — 补全类型定义，去掉 `@ts-ignore`
- **精简中间层** — 移除 mittBus 在 WS 链路上的桥接
- **Agent 保持独立** — 文档化接口约定，不强行合并

---

## 2. 消息信封规范

### 2.1 统一格式

所有 WebSocket 消息使用以下 JSON 结构：

```python
{
    "topic": str,      # 消息主题，如 "notification" / "node_status" / "execution" / "tower"
    "action": str,     # 动作，如 "new" / "update" / "completed" / "progress"
    "payload": dict,   # 具体业务数据
    "timestamp": str,  # ISO 8601 时间戳，如 "2026-06-10T12:00:00Z"
}
```

### 2.2 命名规范

- 使用 **`lower_snake_case`**（与项目 REST API 规范一致）
- 废除 UPPER_SNAKE_CASE 的 `contentType`（如 `SYSTEM`、`NODE_STATUS`）

### 2.3 主题对照表

| topic | action | payload 内容 | 来源 |
|-------|--------|-------------|------|
| `notification` | `unread` | `{count: int}` | 消息中心未读数更新 |
| `notification` | `new` | `{title, content, ...}` | 新消息推送 |
| `node_status` | `update` | `{execution_id, node_id, status}` | Pipeline 节点状态变更 |
| `execution` | `completed` | `{execution_id, status}` | Pipeline 完成/取消 |
| `tower` | `progress` | `{execution_id, node_id, tower_status, progress, artifacts}` | Ansible Tower 作业进度 |
| `system` | `info` | `{message: str}` | 系统提示（连接成功等） |

### 2.4 Channels 内部 type

内部 `channel_layer.group_send()` 的 `type` 统一使用 `"push.message"`，不做多样路由。

---

## 3. 后端架构设计

### 3.1 统一推送模块 `application/ws_push.py`

新建文件，核心接口：

```python
# 推送给单个用户
push_to_user(user_id: int, topic: str, action: str, payload: dict) -> None

# 批量推送给多个用户
push_to_users(user_ids: list[int], topic: str, action: str, payload: dict) -> None
```

内部实现：
- 统一 `_build_message()` 组装标准信封（含 timestamp）
- 统一 `_do_send()` 负责 get_channel_layer + group_send + try-catch
- 统一日志级别（正常跳过→debug，失败→exception）
- 保持 `async_to_sync` 适配 Celery worker 无 event loop 场景

### 3.2 废除 `execution_{id}` 组

| 推送点 | 当前目标 | 新目标 |
|--------|---------|--------|
| `_emit_ws_status()` (tower/polling) | `execution_{id}` | `user_{created_by_id}` |
| `_send_ws_completed()` (flow_engine) | `execution_{id}` | `user_{created_by_id}` |

### 3.3 Consumer 重构

`DvadminWebSocket` 基类职责：
- `connect()` — JWT 认证，加入 `user_{id}` 组，推送未读数
- `disconnect()` — 离开组，清理
- `receive()` — 按 `topic` 路由处理客户端消息

`MegCenter` 当前 `receive()` 中硬编码了 `message_id` 中继查询逻辑，改为按 `topic` 路由。目前前端无主动发消息逻辑（心跳不需要服务端处理），保留 `receive()` 占位供未来扩展。

### 3.4 删除废弃函数

| 函数 | 位置 |
|------|------|
| `websocket_push()` | `websocketConfig.py` + `message_center.py` 重复定义 |
| `create_message_push()` | `websocketConfig.py` |

### 3.5 调用点迁移对照

| 文件 | 当前代码 | 替换为 |
|------|---------|--------|
| `opsflow/signals/handlers.py` | `_push_node_status_via_ws()` 内联 channels | `push_to_user(user_id, "node_status", "update", {...})` |
| `opsflow/core/flow_engine.py` | `_send_ws_completed()` 内联 channels | `push_to_user(user_id, "execution", "completed", {...})` |
| `opsflow/core/tower/polling.py` | `_emit_ws_status()` 推 `execution_{id}` | `push_to_user(user_id, "tower", "progress", {...})` |
| `dvadmin/system/views/message_center.py` | `websocket_push()` 内联 | `push_to_users(users, "notification", "new", {...})` |

### 3.6 Agent Daemon 接口规范（文档化）

与主 WS 体系保持独立，记录接口约定：

| 属性 | 值 |
|------|-----|
| 路由 | `/ws/agent/?token={token}` |
| 依赖库 | `websocket-client`（同步，守护线程） |
| 消息类型 | `exec` / `ping` / `pong` / `heartbeat` / `result` / `log` |
| 心跳 | 30s，应用层 ping/pong |
| 重连 | 指数退避 1-60s |

---

## 4. 前端架构设计

### 4.1 WebSocketService Class

新建 `web/src/utils/websocket.service.ts`，替换当前 `websocket.ts` 对象字面量。

**核心接口：**

```typescript
interface WsMessage {
  topic: string;
  action: string;
  payload: Record<string, any>;
  timestamp: string;
}

class WebSocketService {
  // 事件订阅
  on(topic: string, handler: (msg: WsMessage) => void): void
  off(topic: string, handler: (msg: WsMessage) => void): void

  // 生命周期
  connect(): void
  disconnect(): void

  // 状态
  get isConnected(): boolean
}
```

**内部实现：**
- `topics: Map<string, Set<Function>>` 管理事件订阅
- `onmessage` 解析后按 `topic` 分发到对应 handlers
- `heartbeat` 间隔 30s
- 自动重连 3 次，间隔 5s

### 4.2 移除 mittBus 桥接

当前链路：
```
WebSocket onmessage → detect NODE_STATUS → mittBus.emit → ExecutionDetail.on
```

新链路：
```
WebSocketService onmessage → topic="node_status" → ExecutionDetail wsService.on('node_status')
```

### 4.3 连接生命周期

- `App.vue` 的 `onMounted` 中调用 `wsService.connect()`
- 不再依赖 `watch(route.path)` 触发连接
- 登出时调用 `wsService.disconnect()`
- 保留手动重连 UI

### 4.4 类型定义

新建 `web/src/types/api/socket.d.ts`：

```typescript
interface WsMessage {
  topic: string;
  action: string;
  payload: Record<string, any>;
  timestamp: string;
}

interface WebSocketServiceInstance {
  on(topic: string, handler: (msg: WsMessage) => void): void;
  off(topic: string, handler: (msg: WsMessage) => void): void;
  connect(): void;
  disconnect(): void;
  readonly isConnected: boolean;
}
```

---

## 5. 数据流总览

### 5.1 消息中心推送（改造后）

```
管理员发送消息
  → POST /api/system/message_center/ (REST API)
    → MessageCenterCreateSerializer.save()
      → 写 DB
      → ws_push.push_to_users(users, "notification", "new", {title, content, ...})
        → channel_layer.group_send("user_{id}", {type: "push.message", json: {...}})
          → MegCenter.push_message() → send() → WebSocket
            → WebSocketService onmessage → topic="notification"
              → App.vue 的 handler（更新未读数 + ElNotification）
```

### 5.2 Pipeline 节点状态推送（改造后）

```
bamboo-engine post_set_state 信号
  → on_post_set_state handler
    → _push_node_status_via_ws(execution, node_id)
      → ws_push.push_to_user(execution.created_by_id, "node_status", "update", {...})
        → channel_layer.group_send("user_{id}", ...)
          → WebSocketService onmessage → topic="node_status"
            → ExecutionDetail 的 handler（更新 X6 节点颜色）
```

### 5.3 Tower 作业进度推送（改造后）

```
TowerPollingMixin.poll_job()
  → _emit_ws_status()（每次状态变化）
    → ws_push.push_to_user(creator_id, "tower", "progress", {...})
      → channel_layer.group_send("user_{id}", ...)
        → WebSocketService onmessage → topic="tower"
          → 前端按 execution_id + node_id 匹配对应页面
```

---

## 6. 验证标准

1. WebSocket 握手正常，认证通过后加入 `user_{id}` 组
2. 消息中心发消息后，目标用户收到 SYSTEM 通知 + 未读数更新
3. FlowExecution 节点状态变化后，前端 X6 图实时更新节点颜色
4. Tower 作业轮询过程中进度正常推送
5. 心跳从 2s 改到 30s 后连接稳定（不频繁断连）
6. 断网后自动重连最多 3 次，手动重连按钮正常
7. Agent Daemon 独立连接不受影响
