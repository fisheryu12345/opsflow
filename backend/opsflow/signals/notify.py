"""Notification — WebSocket 节点状态/流程完成通知

通过 _ws_notify（async_to_sync）直接推送，不经过 Celery 队列。
async_to_sync 在线程池中执行异步代码，不会阻塞信号处理器绿色线程，
也不会阻塞 bamboo-engine 的 post_set_state 信号流转。
"""

import logging

from opsflow.tasks import _ws_notify

logger = logging.getLogger(__name__)


def _notify_node_status(execution, node_id, status):
    """直接推送节点状态（async_to_sync，不阻塞，不排队）"""
    _ws_notify(execution.id, node_id, status)


def _notify_completed(execution):
    """直接推送流程完成通知（async_to_sync，不阻塞，不排队）"""
    _ws_notify(execution.id, "__root__", execution.status, msg_type="execution.completed")
