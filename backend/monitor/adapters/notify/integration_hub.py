# -*- coding: utf-8 -*-
"""Integration Hub notify adapter — 复用已有的集成中心通知通道

通过 ConnectorInstance 获取通道配置，调用对应适配器发送通知。
"""

import logging

from .. import BaseNotifyAdapter, NotifyMessage, NotifyResult

logger = logging.getLogger(__name__)
FSM = 'intg_hub_adapter'


class IntegrationHubNotify(BaseNotifyAdapter):
    """
    集成中心通知适配器
    复用 integration 模块的 ConnectorInstance 管理通知通道配置。
    支持的通道: wecom / dingtalk / email / sms / webhook
    """

    def send(self, recipients: list, message: NotifyMessage) -> NotifyResult:
        channel = self.config.get('channel', 'webhook')
        connector_code = self.config.get('connector_code', '')

        try:
            from integration.models import ConnectorInstance, ConnectorDefinition
            from integration.services.credential_service import decrypt_credential

            # 查找连接器实例
            if connector_code:
                instances = ConnectorInstance.objects.filter(
                    definition__code=connector_code,
                    is_active=True,
                )[:1]
            else:
                instances = ConnectorInstance.objects.filter(
                    definition__category='notification',
                    is_active=True,
                )[:1]

            if not instances:
                logger.warning(f"[IntegrationHub] No active connector for channel={channel}")
                return NotifyResult(success=False, message='No active connector')

            instance = instances[0]
            config = instance.config or {}
            webhook_url = config.get('webhook_url', '') or config.get('url', '')

            # 发送 HTTP POST
            if webhook_url:
                import requests
                payload = {
                    'title': message.title,
                    'content': message.content,
                    'severity': message.severity,
                    'alert_id': message.alert_id,
                    'recipients': recipients,
                }
                resp = requests.post(webhook_url, json=payload, timeout=15)
                resp.raise_for_status()
                logger.info(f"[IntegrationHub] Notify sent to {channel}: {resp.status_code}")
                return NotifyResult(success=True, message=f'Sent ({resp.status_code})')

            return NotifyResult(success=False, message='No webhook_url configured')

        except ImportError:
            logger.warning("[IntegrationHub] integration module not available")
            return NotifyResult(success=False, message='Integration module unavailable')
        except Exception as e:
            logger.error(f"[IntegrationHub] Send failed: {e}")
            return NotifyResult(success=False, message=str(e))
