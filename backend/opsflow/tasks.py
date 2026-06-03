import asyncio
import concurrent.futures
import json
import logging

from celery import shared_task

logger = logging.getLogger(__name__)

# WebSocket 通知的超时秒数。超过此时间未完成则放弃推送，避免阻塞 worker greenlet。
_NOTIFY_TIMEOUT = 15


def run_async(coro):
    """在 Celery worker 中安全执行异步协程。

    Celery worker 可能已有运行中的事件循环（如 -P gevent 模式），
    此时 asyncio.new_event_loop() + run_until_complete 会报错。

    处理策略：
    - 有运行中循环 → run_coroutine_threadsafe + timeout 防止死锁
    - 无运行中循环 → 创建临时事件循环执行并关闭

    WS 推送是 best-effort 通知，避免阻塞 worker。
    """
    import uuid
    _req_id = uuid.uuid4().hex[:8]
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=_NOTIFY_TIMEOUT)
    except concurrent.futures.TimeoutError:
        logger.warning(
            "[req=%s] run_async timed-out after %ss (WS message lost, pipeline continues)",
            _req_id, _NOTIFY_TIMEOUT,
        )
        return None
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=30, queue='er_execute')
def execute_pipeline_task(self, execution_id):
    """Celery 任务 — 异步执行 Pipeline"""
    from opsflow.models import FlowExecution
    from opsflow.core.flow_engine import FlowEngine
    try:
        execution = FlowExecution.objects.get(id=execution_id)
        engine = FlowEngine(execution)
        engine.run()
    except FlowExecution.DoesNotExist:
        pass
    except Exception as exc:
        raise self.retry(exc=exc)


_CHANNEL_REDIS_PREFIX = "asgi"


def _ws_notify(execution_id, node_id, status, message=""):
    """同步推送节点状态到 WebSocket，通过 Redis pub/sub 直接写入 channel layer。

    不使用 channels_redis 的 async API（在 Celery worker 中跨临时事件循环时
    Redis 异步连接会过期），改用同步 Redis 直连 + channels_redis 内部 key 格式。
    """
    import redis

    host = "127.0.0.1"
    port = 6379
    db = 0

    try:
        r = redis.Redis(host=host, port=port, db=db, socket_connect_timeout=3)
        group = f"execution_{execution_id}"
        payload = json.dumps(
            {
                "type": "node_status",
                "node_id": node_id,
                "status": status,
                "message": message,
            }
        )
        group_key = f"{_CHANNEL_REDIS_PREFIX}:g:{group}"
        channel_names = r.zrange(group_key, 0, -1)
        for ch in channel_names:
            if isinstance(ch, bytes):
                ch = ch.decode()
            r.publish(f"{_CHANNEL_REDIS_PREFIX}:{ch}", payload)
    except Exception as e:
        logger.warning(
            "WS notify best-effort failed for execution %s: %s "
            "(pipeline continues, UI may miss real-time update)",
            execution_id,
            e,
        )


@shared_task(queue='er_execute')
def notify_node_status(execution_id, node_id, status, message=''):
    """Celery 任务 — 推送节点状态到 WebSocket（通过同步 Redis pub/sub）

    避免使用 channels_redis 的 async API，改用同步 Redis 直连写入
    channel layer 的 pub/sub 通道。
    """
    _ws_notify(execution_id, node_id, status, message)


@shared_task(queue='er_execute')
def notify_execution_completed(execution_id, execution_status):
    """Celery 任务 — 推送执行完成通知到 WebSocket

    使用与 notify_node_status 相同的队列（er_execute），确保消息有序：
    notify_node_status 先入队 → notify_execution_completed 后入队，
    Celery 按 FIFO 顺序投递，避免 execution_completed 先于节点状态
    到达前端的时序竞争。
    """
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    run_async(
        channel_layer.group_send(
            f"execution_{execution_id}",
            {"type": "execution.completed", "status": execution_status},
        )
    )


@shared_task(bind=True, max_retries=0)
def auto_retry_node_task(self, execution_id, node_id):
    """Celery 任务 — 自动重试失败节点（由 auto_retry dispatch 触发）

    参考 bk_sops auto_retry_node Celery 任务
    """
    from opsflow.models import FlowExecution, AutoRetryStrategy
    from opsflow.core.flow_engine import FlowEngine

    try:
        execution = FlowExecution.objects.get(id=execution_id)
        strategy = AutoRetryStrategy.objects.get(
            execution=execution, node_id=node_id,
        )

        # 自增重试计数器
        strategy.retry_times += 1
        strategy.save(update_fields=['retry_times'])

        # 执行重试
        engine = FlowEngine(execution)
        engine.retry(node_id)

        logger.info(
            "[AutoRetry] Node %s auto-retried (%d/%d)",
            node_id, strategy.retry_times, strategy.max_retry_times,
        )

    except FlowExecution.DoesNotExist:
        logger.error("[AutoRetry] Execution %s not found", execution_id)
    except AutoRetryStrategy.DoesNotExist:
        logger.error("[AutoRetry] Strategy not found for exec=%s node=%s", execution_id, node_id)
    except Exception as exc:
        logger.exception("[AutoRetry] Error retrying node %s: %s", node_id, exc)


@shared_task(queue='er_execute')
def execute_node_timeout_strategy(execution_id, node_id, action):
    """Celery 任务 — 执行节点超时策略

    在 dispatch_timeout_nodes 发现到期节点后调用。
    """
    from opsflow.models import FlowExecution, NodeTimeoutConfig
    from opsflow.core.node_timeout_strategy import NODE_TIMEOUT_HANDLER

    try:
        execution = FlowExecution.objects.get(id=execution_id)
        config = NodeTimeoutConfig.objects.get(
            execution=execution, node_id=node_id,
        )
        handler = NODE_TIMEOUT_HANDLER.get(action)
        if handler:
            handler.deal_with_timeout_node(execution, node_id, config)
    except Exception as e:
        logger.exception("[Timeout] execute strategy error for node %s: %s", node_id, e)


@shared_task(bind=True, max_retries=0)
def webhook_send(self, webhook_id, execution_id, event):
    """Celery 任务 — 发送 Webhook 回调"""
    from opsflow.core.webhook_service import WebhookService
    try:
        WebhookService.send(webhook_id, execution_id, event)
    except Exception as e:
        logger.exception("[Webhook] send error: %s", e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def retry_schedule_execution(self, plan_id, plan_max_retries=None):
    """Celery 任务 — 重试调度计划执行

    Args:
        plan_id: SchedulePlan ID
        plan_max_retries: 来自 plan.max_retries，覆盖 task 默认值
    """
    # 用 plan.max_retries 覆盖任务的默认 max_retries
    if plan_max_retries is not None and plan_max_retries > 0:
        self.max_retries = plan_max_retries
    from opsflow.core.scheduler_service import opsflow_scheduler
    try:
        opsflow_scheduler._execute_plan(plan_id)
    except Exception as exc:
        raise self.retry(exc=exc)
