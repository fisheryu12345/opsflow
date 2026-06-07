# 注意事项

## 1. Celery App 导入

`application/__init__.py` 必须包含以下导入，否则 Django web 进程中 Celery task 的 `delay()` / `apply_async()` 无法获取 `broker_url` 等配置，会回退到默认 AMQP（localhost:5672），导致 `WinError 10061` 连接被拒绝：

```python
from .celery import app as celery_app
```

### 现象

- `start` 等 API 返回 `code: 4000`，msg 为 `WinError 10061`
- 但 `execution.status` 已更新为 `running`（因为异常发生在 `status.save()` 之后）
- Celery worker 进程正常，直连 Redis 正常
- 原因：web 进程调用 `@shared_task.delay()` 时，Celery 配置未加载

## 2. Celery Worker 队列

OpsFlow pipeline 使用两个专用队列：

| 队列 | 用途 |
|------|------|
| `er_execute` | 节点执行任务（bamboo-engine 调度） |
| `er_schedule` | 定时/轮询任务（bamboo-engine 调度） |

启动 worker 时需同时监听这两个队列：

```bash
celery -A application worker -Q er_execute,er_schedule -l info -P gevent
```

`opsflow.tasks.execute_pipeline_task` 已显式指定 `queue='er_execute'`。

## 3. pipeline.contrib.node_timeout

`pipeline.contrib.node_timeout` **不可直接注册到 INSTALLED_APPS**。其 `apps.py` 的 `ready()` 方法检查 `hasattr(settings, "redis_inst")`，但 Django 的 `LazySettings` 仅暴露大写属性，即使通过 `SimpleLazyObject` 注入也无法通过 `hasattr` 检测。

正确用法：只作为库调用，在 `bamboo_builder.py` 中 `import` 后直接使用：

```python
from pipeline.contrib.node_timeout import apply_node_timout_configs
apply_node_timout_configs(tree, timeout_configs)
```

已用 `try/except ImportError` 包裹，导入失败时不影响流程执行。

## 4. Redis 密码

当前 Redis 服务器无密码。如果后续启用密码，需要修改 settings.py 中三处配置：

```python
# CACHES OPTIONS — 添加 PASSWORD
"CACHES": {"default": {"OPTIONS": {"PASSWORD": "your_password"}}}

# Celery broker URL
CELERY_BROKER_URL = 'redis://:password@127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://:password@127.0.0.1:6379/1'
```

## 5. 首次流程测试步骤

```
1. POST /api/login/          → 获取 JWT token
2. POST /api/opsflow/templates/  → 创建模板（pipeline_tree 含 test_print_time）
3. POST /api/opsflow/executions/ → 创建执行实例（引用 template）
4. POST /api/opsflow/executions/{id}/start/ → 启动执行
5. GET  /api/opsflow/executions/{id}/       → 等待 status=completed
6. GET  /api/opsflow/logs/?execution={id}   → 查看执行日志
```

## 6. WebSocket Channel Layer 跨进程通信

### 背景

Pipeline 执行过程中需要将节点状态变更实时推送到前端 WebSocket。推送链路如下：

```
bamboo-engine 节点状态变更
  → post_set_state 信号（signals.py）
    → _notify_node_status() → notify_node_status.delay()  [Celery 任务]
    → _notify_completed()                                [直接调用]
       └── 两者最终都调用 channel_layer.group_send() 发 WS 消息
```

### 问题

两个问题叠加导致 WS 推送不可用：

**问题 1：async_to_sync 在 Celery worker 中报错**

```
RuntimeError: You cannot use AsyncToSync in the same thread
as an async event loop - just await the async function directly.
```

`asgiref.sync.async_to_sync` 内部调用 `asyncio.run()`，该方法要求当前线程**没有运行中的事件循环**。由于 `DJANGO_ALLOW_ASYNC_UNSAFE = 'true'` 开启了异步兼容模式，Celery worker 线程中某些 import 链路可能已启动事件循环，导致冲突。

**问题 2：InMemoryChannelLayer 跨不了进程**

原始配置使用 `channels.layers.InMemoryChannelLayer`，该实现的消息**仅在进程内内存有效**。ASGI 服务（Daphne/Uvicorn）和 Celery worker 是**不同进程**，所以：

- Celery worker 中 `notify_node_status` 任务发出的 WS 消息 → 发到了 worker 进程自己的内存通道
- 前端 WebSocket 客户端连的是 ASGI 进程 → 收不到这条消息

即使 `async_to_sync` 不报错，消息也到不了前端。

### 解决方法

两步修复：

**1. InMemoryChannelLayer → RedisChannelLayer**

```python
# settings.py
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

所有进程（ASGI + Celery worker）通过 Redis 共享消息通道，谁发的消息其他进程都能消费。

**2. async_to_sync → 手动事件循环**

所有调用 `channel_layer.group_send()` 的地方改为手动创建事件循环：

```python
import asyncio
loop = asyncio.new_event_loop()
try:
    asyncio.set_event_loop(loop)
    loop.run_until_complete(channel_layer.group_send(...))
finally:
    loop.close()
```

### 影响文件

| 文件 | 方法/函数 | 改动 |
|------|-----------|------|
| `settings.py` | CHANNEL_LAYERS | InMemory → Redis |
| `tasks.py` | `notify_node_status` | async_to_sync → 手动 loop |
| `signals.py` | `_notify_completed` | async_to_sync → 手动 loop |
| `flow_engine.py` | `_send_ws_node_status` | async_to_sync → 手动 loop |
| `flow_engine.py` | `_send_ws_completed` | async_to_sync → 手动 loop |

### 信号处理器的两种 WS 推送方式

`signals.py` 的 `on_post_set_state` 信号处理器中，原作者对两种场景采用了不同的推送方式：

| 场景 | 方法 | 方式 | 理由 |
|------|------|------|------|
| 节点状态变更（频繁） | `_notify_node_status` → `notify_node_status.delay()` | 走 Celery 任务 | 不阻塞 pipelin 执行流 |
| pipeline 完成（一次） | `_notify_completed` → 直接调 channel_layer | 直接调用 | 执行已结束，无阻塞顾虑 |

两种方式都改为手动事件循环。后者 `_notify_completed`（signals.py 第 145 行）不走 Celery，直接在信号处理器上下文中推送。注意信号处理器本身也运行在 Celery worker 中，所以同样会遇到 async_to_sync 的问题。

### 相关 Celery Worker 启动命令

需确保 Redis 正在运行，且 worker 使用 gevent 池模式以支持协程并发：

```bash
celery -A application worker -Q er_execute,er_schedule,default \
  -l info -P gevent -c 10
```

`-P gevent` 与手动事件循环的 `asyncio.new_event_loop()` 不冲突，gevent 处理的是网络 I/O 并发，手动事件循环处理的是调用 asyncio 协程的执行环境。

## 7. Redis 版本兼容性 — BZPOPMIN

### 背景

`channels_redis.RedisChannelLayer` 内部使用 `BZPOPMIN` 命令从有序集合中阻塞式弹出消息。该命令是 **Redis 5.0+** 引入的，低版本 Redis（如 3.x、4.x）不支持。

项目中 Redis 曾为 **3.0.504**（Windows 移植版），使用 `RedisChannelLayer` 时触发：

```
redis.exceptions.ResponseError: unknown command 'BZPOPMIN'
```

### 影响范围

- 所有依赖 WebSocket 推送的功能：节点状态实时更新、pipeline 执行进度推送
- `RedisChannelLayer` 初始化不会报错，但第一次尝试从有序集合读取消息时立即崩溃
- Django ASGI 进程和 Celery worker 中的 `channel_layer.group_send()` 均受影响

### 诊断方法

```python
import redis
r = redis.Redis(host='127.0.0.1', port=6379)
r.info().get('redis_version')  # 3.x → 不兼容，5.x+ → 正常
```

### 解决方案

将 Redis 升级到 **5.0 或更高版本**。

当前环境已升级到 **Redis 5.0.14.1**，经测试 `BZPOPMIN` 正常：

```
PING: True
SET/GET: OK
BZPOPMIN: 可用
```

### Windows 下的 Redis 升级建议

- **Memurai**（推荐）：Windows 原生 Redis 兼容实现，支持 Redis 5/6/7 API，可作为 Windows 服务运行
- **Docker Desktop**：拉取 `redis:7-alpine` 镜像运行
- 避免使用 3.x 的 Windows 移植版

## 8. USE_TZ 环境差异 — APScheduler datetime 兼容（影响流程调度）

### 背景

- **开发环境**：`USE_TZ = False`（`backend/application/settings.py`）
- **生产环境**：`USE_TZ = True`

由于开发环境 `USE_TZ=False`，MySQL 不支持存入 timezone-aware 的 datetime，而 APScheduler 的 `CronTrigger.get_next_fire_time()` 和 `job.next_run_time` 返回的始终是 timezone-aware datetime（不受 Django 设置影响）。

### 现象

**受影响功能：流程调度（SchedulePlan）的创建、更新和执行。** 具体来说，`SchedulePlan` 的 `next_run_at` 和 `last_run_at` 字段在写入数据库时触发此问题。

创建或更新调度计划时，`_sync_next_run` 向 `SchedulePlan.next_run_at` 写入 aware datetime，MySQL 报错：

```
ValueError: MySQL backend does not support timezone-aware datetimes when USE_TZ is False.
```

### 解决方法

在 `scheduler_service.py` 定义了 `_naive()` 工具函数，统一去除 datetime 的时区信息：

```python
def _naive(dt):
    """确保 datetime 是 naive 的（去除时区），兼容 USE_TZ=False + MySQL"""
    if dt is not None and hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt
```

所有从 APScheduler 获取的 datetime（`job.next_run_time`、`trigger.get_next_fire_time()`）和用户传入的 `scheduled_at` 在保存到数据库之前，均通过 `_naive()` 过滤。

### 部署注意

- 开发环境（`USE_TZ=False`）：`_naive()` 实际生效，去除时区
- 生产环境（`USE_TZ=True`）：`_naive()` 是空操作（datetime 存入 MySQL 前 Django 会自动处理），不会产生副作用
- `_naive()` 不需要在生产环境移除，兼容两者

## 9. 已知限制

- `bamboo-pipeline` 4.0.2 安装时会降级 `redis` 7.4.0 → 5.3.1、`django-timezone-field` 6.0.1 → 5.1，属正常依赖兼容
- BambooDjangoRuntime 的 Process/Node 记录存储在 MySQL `pipeline_*` 表中，与 OpsFlow 的 `FlowExecution`/`OpsLog` 独立
- 节点状态追踪通过 `post_set_state` 信号异步完成，`FlowExecution.node_status` 的更新依赖于 signals.py 的信号处理器正确注册
