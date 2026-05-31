import asyncio
import concurrent.futures
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


@shared_task(queue='er_execute')
def notify_node_status(execution_id, node_id, status, message=''):
    """Celery 任务 — 推送节点状态到 WebSocket（通过 Redis channel layer）

    不能使用 asgiref.sync.async_to_sync，因为 Celery worker 中可能已有
    运行中的事件循环（DJANGO_ALLOW_ASYNC_UNSAFE 开启时），async_to_sync
    内部调用 asyncio.run() 会抛出 RuntimeError。

    改用 asyncio.new_event_loop() + run_until_complete，手动管理事件循环
    生命周期，确保 loop 用完即关。
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    run_async(
        channel_layer.group_send(
            f'execution_{execution_id}',
            {
                'type': 'node_status',
                'node_id': node_id,
                'status': status,
                'message': message,
            }
        )
    )
