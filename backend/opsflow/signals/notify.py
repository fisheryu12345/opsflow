"""Notification — WebSocket 节点状态/流程完成通知

负责通过 Django Channels 向 WebSocket 客户端推送节点状态变更
和流程完成事件。

所有通知统一走 Celery 任务（er_execute 队列），保证消息投递
顺序：节点状态通知先入队 → 执行完成通知后入队，Celery FIFO
保证前端不会先收到 execution_completed 再收到节点 status。
"""

import logging

from opsflow.tasks import notify_node_status, notify_execution_completed

logger = logging.getLogger(__name__)


def _notify_node_status(execution, node_id, status):
    """推送节点状态变更到 WebSocket（通过 Celery 任务）"""
    notify_node_status.delay(execution.id, node_id, status)


def _notify_completed(execution):
    """推送流程完成通知到 WebSocket（通过 Celery 任务）

    与 _notify_node_status 使用同一队列（er_execute），确保：
    通知顺序 = 入队顺序 → 前端先收到所有节点终态，再收到完成事件。
    """
    notify_execution_completed.delay(execution.id, execution.status)
