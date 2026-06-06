"""Notification — WebSocket 节点状态/流程完成通知

负责通过 Django Channels 向 WebSocket 客户端推送节点状态变更
和流程完成事件。

使用 channel_layer.group_send 标准 API（与 notify_execution_completed 一致），
避免直接操作 Redis 内部 key 格式导致的兼容性问题。
"""

import logging

from channels.layers import get_channel_layer
from opsflow.tasks import run_async

logger = logging.getLogger(__name__)


def _notify_node_status(execution, node_id, status):
    """推送节点状态变更到 WebSocket"""
    from opsflow.tasks import _ws_notify
    _ws_notify(execution.id, node_id, status)


def _notify_completed(execution):
    """推送流程完成通知到 WebSocket（execution_completed 类型）"""
    channel_layer = get_channel_layer()
    run_async(
        channel_layer.group_send(
            f"execution_{execution.id}",
            {"type": "execution.completed", "status": execution.status},
        )
    )
