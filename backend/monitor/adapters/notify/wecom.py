# -*- coding: utf-8 -*-
"""WeCom (企业微信) notify adapter — 通过机器人 Webhook 发送告警通知"""

import logging

import requests

from .. import BaseNotifyAdapter, NotifyMessage, NotifyResult

logger = logging.getLogger(__name__)
FSM = 'wecom_adapter'


class WeComNotify(BaseNotifyAdapter):
    """企业微信机器人通知适配器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.webhook_url = config.get('webhook_url', '')
        self.mentioned_list = config.get('mentioned_list', [])

    def send(self, recipients: list, message: NotifyMessage) -> NotifyResult:
        if not self.webhook_url:
            return NotifyResult(success=False, message='webhook_url not configured')

        severity_label = {1: '🔴 致命', 2: '🟡 预警', 3: '🔵 提醒'}

        content = f"""**{message.title}**
> 级别: {severity_label.get(message.severity, '未知')}
> {message.content}"""

        payload = {
            'msgtype': 'markdown',
            'markdown': {'content': content},
        }

        if self.mentioned_list:
            payload['markdown']['mentioned_list'] = self.mentioned_list

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            if result.get('errcode') == 0:
                logger.info(f"[WeCom] Notify sent: {message.alert_id}")
                return NotifyResult(success=True, message='Sent')
            return NotifyResult(success=False, message=result.get('errmsg', ''))
        except requests.RequestException as e:
            logger.error(f"[WeCom] Send failed: {e}")
            return NotifyResult(success=False, message=str(e))
