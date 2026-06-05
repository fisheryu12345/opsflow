# -*- coding: utf-8 -*-
"""DingTalk (钉钉) notify adapter — 通过机器人 Webhook 发送告警通知"""

import logging
import time
import hashlib
import base64

import requests

from .. import BaseNotifyAdapter, NotifyMessage, NotifyResult

logger = logging.getLogger(__name__)
FSM = 'dingtalk_adapter'


class DingTalkNotify(BaseNotifyAdapter):
    """钉钉机器人通知适配器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.webhook_url = config.get('webhook_url', '')
        self.secret = config.get('secret', '')

    def _sign(self) -> str:
        """钉钉签名"""
        if not self.secret:
            return self.webhook_url
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.secret}'
        hmac_code = hashlib.sha256(string_to_sign.encode('utf-8')).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return f'{self.webhook_url}&timestamp={timestamp}&sign={sign}'

    def send(self, recipients: list, message: NotifyMessage) -> NotifyResult:
        if not self.webhook_url:
            return NotifyResult(success=False, message='webhook_url not configured')

        severity_label = {1: '致命', 2: '预警', 3: '提醒'}
        title = f"[{severity_label.get(message.severity, '通知')}] {message.title}"

        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'title': title,
                'text': f"# {title}\n{message.content}\n---\n告警ID: {message.alert_id}",
            },
        }

        url = self._sign()
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            if result.get('errcode') == 0:
                return NotifyResult(success=True, message='Sent')
            return NotifyResult(success=False, message=result.get('errmsg', ''))
        except requests.RequestException as e:
            logger.error(f"[DingTalk] Send failed: {e}")
            return NotifyResult(success=False, message=str(e))
