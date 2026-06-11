# -*- coding: utf-8 -*-
"""Unified WebSocket push utility — single entry point for all Channels group_send

所有 Channels WebSocket 推送必须通过此模块，不再重复获取 channel_layer
或自行处理 async_to_sync / try-catch。
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

# 推送超时秒数（Celery worker 中 async_to_sync 等待上限）
_PUSH_TIMEOUT = 15


def _build_message(topic: str, action: str, payload: dict) -> dict:
    """组装统一消息信封

    所有 WebSocket 消息使用统一的 topic/action/payload/timestamp 格式。
    """
    return {
        "topic": topic,
        "action": action,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _do_send(group_name: str, message: dict) -> None:
    """执行 channel_layer.group_send，统一异常处理

    Args:
        group_name: Channels group 名，如 "user_42"
        message: 已组装好的完整消息字典
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.debug(
                "[ws_push] channel_layer unavailable, group=%s topic=%s",
                group_name,
                message.get("topic"),
            )
            return
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "push.message",
                "json": message,
            },
        )
    except Exception:
        logger.exception(
            "[ws_push] group_send failed group=%s topic=%s",
            group_name,
            message.get("topic"),
        )


def push_to_user(
    user_id: int,
    topic: str,
    action: str,
    payload: dict,
) -> None:
    """推送给指定用户

    Args:
        user_id: 目标用户 ID（推送到 user_{id} 组）
        topic: 消息主题，如 "notification" / "node_status" / "execution"
        action: 动作，如 "new" / "update" / "completed"
        payload: 业务数据字典
    """
    msg = _build_message(topic, action, payload)
    _do_send(f"user_{user_id}", msg)


def push_to_users(
    user_ids: list[int],
    topic: str,
    action: str,
    payload: dict,
) -> None:
    """批量推送给多个用户

    Args:
        user_ids: 目标用户 ID 列表
        topic: 消息主题
        action: 动作
        payload: 业务数据字典
    """
    if not user_ids:
        return
    msg = _build_message(topic, action, payload)
    for uid in user_ids:
        _do_send(f"user_{uid}", msg)
