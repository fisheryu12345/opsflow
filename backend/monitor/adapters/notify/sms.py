# -*- coding: utf-8 -*-
"""SMS notify adapter stub — 短信通知适配器 (需对接具体短信网关)"""

from .. import BaseNotifyAdapter, NotifyMessage, NotifyResult


class SmsNotify(BaseNotifyAdapter):
    """短信通知适配器 — 通过 Integration Hub 短信连接器发送"""

    def send(self, recipients: list, message: NotifyMessage) -> NotifyResult:
        try:
            from integration.adapters.notification.sms import AliyunSmsConnector
            connector = AliyunSmsConnector(self.config)
            for phone in recipients:
                connector.send_sms(phone, {
                    'title': message.title[:20],
                    'content': message.content[:50],
                })
            return NotifyResult(success=True, message=f'Sent to {len(recipients)}')
        except ImportError:
            return NotifyResult(success=False, message='Aliyun SMS SDK not available')
        except Exception as e:
            return NotifyResult(success=False, message=str(e))
