import asyncio
import concurrent.futures
import json
import logging

from celery import shared_task

logger = logging.getLogger(__name__)

# WebSocket 通知的超时秒数。超过此时间未完成则放弃推送，避免阻塞 worker greenlet。
_NOTIFY_TIMEOUT = 5


def run_async(coro):
    """在 Celery worker 中安全执行异步协程。

    Celery worker 可能已有运行中的事件循环（如 -P gevent 模式），
    此时 asyncio.new_event_loop() + run_until_complete 会报错。

    处理策略：
    - 有运行中循环 → run_coroutine_threadsafe + timeout 防止死锁
    - 无运行中循环 → 创建临时事件循环执行并关闭

    WS 推送是 best-effort 通知，5s 超时后放弃、记录警告、不抛异常。
    """
    try:
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=_NOTIFY_TIMEOUT)
    except concurrent.futures.TimeoutError:
        logger.warning(
            "run_async timed-out after %ss (WS message lost, pipeline continues)",
            _NOTIFY_TIMEOUT,
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


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def retry_schedule_execution(self, plan_id):
    """Celery 任务 — 重试调度计划执行"""
    from opsflow.core.scheduler_service import opsflow_scheduler
    try:
        opsflow_scheduler._execute_plan(plan_id)
    except Exception as exc:
        raise self.retry(exc=exc)
