# -*- coding: utf-8 -*-
from __future__ import annotations

"""EventDispatcher — CMDB CI 事件分发服务

当模型实例发生创建/更新/删除时，遍历所有匹配的 EventSubscription，
向配置的 Webhook URL 发送 POST 请求推送变更通知。
"""

import json
import logging
from typing import Optional

from django.conf import settings

from ..models.event_subscription import EventSubscription

logger = logging.getLogger(__name__)

FSM = 'event_dispatcher'

# 事件类型映射：change_tracker 传过来的 event_type → subscription 中的 event_type
EVENT_TYPE_MAP = {
    'create': 'instance.create',
    'update': 'instance.update',
    'delete': 'instance.delete',
}


def dispatch_event(event_type: str,
                   model_code: str,
                   instance_id: str,
                   operator: str,
                   changes: Optional[list] = None):
    """分发事件到所有匹配的订阅

    Args:
        event_type: create / update / delete
        model_code: 模型编码
        instance_id: 实例 ID
        operator: 操作人
        changes: 变更详情列表 [{field, old_value, new_value}, ...]
    """
    mapped_event = EVENT_TYPE_MAP.get(event_type)
    if not mapped_event:
        logger.warning(f"{FSM} 未知事件类型: {event_type}")
        return

    # 查询匹配的订阅（全模型匹配 或 指定模型匹配）
    subscriptions = EventSubscription.objects.filter(
        is_active=True,
    )
    # 过滤：全模型订阅 (model_code='*') 或 匹配当前模型
    matched = [
        sub for sub in subscriptions
        if sub.model_code in ('*', model_code)
        and sub.event_type == mapped_event
    ]

    if not matched:
        logger.debug(f"{FSM} 无匹配订阅: {model_code}/{event_type}")
        return

    # 构建 payload
    payload = {
        'event_type': mapped_event,
        'model_code': model_code,
        'instance_id': instance_id,
        'operator': operator,
        'changes': changes or [],
        'source': 'cmdb',
    }

    # 分发到每个订阅
    for sub in matched:
        _send_webhook(sub, payload)


def _send_webhook(subscription: EventSubscription, payload: dict):
    """向单个订阅发送 webhook POST 请求"""
    import requests

    try:
        timeout = getattr(settings, 'CMDB_WEBHOOK_TIMEOUT', 10)
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(
            subscription.endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        if resp.ok:
            logger.info(f"{FSM} 推送成功: {subscription.endpoint} "
                         f"({subscription.model_code}/{subscription.event_type})")
        else:
            logger.warning(f"{FSM} 推送失败 [{resp.status_code}]: "
                           f"{subscription.endpoint} — {resp.text[:200]}")
    except requests.RequestException as e:
        logger.error(f"{FSM} 推送异常: {subscription.endpoint} — {e}")
