"""Notification — WebSocket 节点状态/流程完成通知

负责通过 Django Channels 向 WebSocket 客户端推送节点状态变更
和流程完成事件。
"""

import logging

from channels.layers import get_channel_layer
from opsflow.tasks import notify_node_status, run_async

logger = logging.getLogger(__name__)


def _notify_node_status(execution, node_id, status):
    """推送节点状态变更到 WebSocket"""
    notify_node_status.delay(execution.id, node_id, status)


def _notify_completed(execution):
    """推送流程完成通知到 WebSocket

    使用 tasks.run_async 统一处理事件循环兼容性，避免在 Celery gevent
    工作线程中直接使用 asyncio.new_event_loop() 导致 "Cannot run the
    event loop while another loop is running" 错误。
    """
    channel_layer = get_channel_layer()
    run_async(
        channel_layer.group_send(
            f"execution_{execution.id}",
            {"type": "execution.completed", "status": execution.status},
        )
    )
