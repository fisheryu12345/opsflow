"""Webhook dispatch service — push events to third-party systems

Webhook 推送服务 — 当平台事件发生时，通知已订阅的第三方系统
"""

import json
import logging
import hashlib
import hmac
from datetime import datetime

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

FSM = 'webhook_dispatch'


def dispatch_webhook(event_type: str, payload: dict) -> list:
    """
    向所有订阅了该事件类型的 Webhook 推送消息
    返回 [(subscription_id, success), ...]
    """
    from ..models.models import WebhookSubscription

    results = []
    subs = WebhookSubscription.objects.filter(
        event_type=event_type, is_active=True
    )
    for sub in subs:
        success = _send_webhook(sub, payload)
        sub.last_delivery_at = timezone.now()
        sub.last_delivery_status = 'success' if success else 'failed'
        sub.save(update_fields=['last_delivery_at', 'last_delivery_status'])
        results.append((sub.id, success))
    return results


def _send_webhook(subscription, payload: dict) -> bool:
    """发送单个 Webhook 回调"""
    headers = {'Content-Type': 'application/json'}
    body = json.dumps(payload, default=str)

    # 签名
    if subscription.secret:
        signature = hmac.new(
            subscription.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()
        headers['X-OpsFlow-Signature'] = signature

    for attempt in range(subscription.retry_count + 1):
        try:
            resp = requests.post(
                subscription.callback_url,
                data=body,
                headers=headers,
                timeout=30,
            )
            if resp.ok:
                logger.info(f"Webhook 推送成功 [{subscription.name}]: {subscription.callback_url}")
                return True
            else:
                logger.warning(f"Webhook HTTP {resp.status_code} [{subscription.name}] (attempt {attempt + 1})")
        except requests.RequestException as e:
            logger.error(f"Webhook 推送失败 [{subscription.name}]: {e} (attempt {attempt + 1})")

        if attempt < subscription.retry_count:
            import time
            time.sleep(subscription.retry_interval)

    return False
