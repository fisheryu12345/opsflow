"""Notification — WebSocket 节点状态/流程完成通知

负责通过 Django Channels 向 WebSocket 客户端推送节点状态变更
和流程完成事件。

所有状态变更统一同步直发 Redis pub/sub（_ws_notify 仅 ~0.5ms），
避免 Celery 排队延迟导致前端颜色更新滞后。
"""

import logging

from opsflow.tasks import _ws_notify

logger = logging.getLogger(__name__)


def _notify_node_status(execution, node_id, status):
    """推送节点状态变更到 WebSocket（同步直发，不排队）"""
    _ws_notify(execution.id, node_id, status)


def _notify_completed(execution):
    """推送流程完成通知到 WebSocket（同步直发，不排队）"""
    _ws_notify(execution.id, "__root__", execution.status)
