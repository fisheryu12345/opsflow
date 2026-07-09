# -*- coding: utf-8 -*-
"""ITSM 通知服务 — 状态变更时的消息通知

支持的通知方式:
  - 站内通知 (WebSocket / ticket.meta 存储)
  - 企业微信机器人 (WeCom Robot)
  - 钉钉机器人 (DingTalk Robot)
  - 邮件通知 (SMTP)
"""

import json
import logging
import urllib.request
import urllib.error
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

logger = logging.getLogger(__name__)


# ========== Channel implementations ==========

def send_wecom_notify(webhook_url: str, title: str, content: str) -> bool:
    """企业微信机器人消息

    参考: https://developer.work.weixin.qq.com/document/path/91770
    """
    if not webhook_url:
        logger.warning('[WeCom] No webhook_url provided')
        return False
    try:
        payload = json.dumps({
            'msgtype': 'markdown',
            'markdown': {
                'content': f'## {title}\n{content}',
            }
        }).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get('errcode') == 0:
                logger.info('[WeCom] Notify sent successfully')
                return True
            logger.warning(f'[WeCom] Send failed: {result}')
            return False
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        logger.error(f'[WeCom] Request error: {e}')
        return False


def send_dingtalk_notify(webhook_url: str, title: str, content: str) -> bool:
    """钉钉机器人消息

    参考: https://open.dingtalk.com/document/group/custom-robot-access
    """
    if not webhook_url:
        logger.warning('[DingTalk] No webhook_url provided')
        return False
    try:
        payload = json.dumps({
            'msgtype': 'markdown',
            'markdown': {
                'title': title,
                'text': f'## {title}\n{content}',
            }
        }).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get('errcode') == 0:
                logger.info('[DingTalk] Notify sent successfully')
                return True
            logger.warning(f'[DingTalk] Send failed: {result}')
            return False
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        logger.error(f'[DingTalk] Request error: {e}')
        return False


def send_email_notify(smtp_config: dict, recipients: list, title: str, content: str) -> bool:
    """SMTP 邮件通知

    smtp_config:
        host: SMTP 服务器地址
        port: SMTP 端口
        user: 发件人用户名
        password: 发件人密码/授权码
        use_tls: 是否使用 TLS (默认 True)
        from_addr: 发件人地址
    """
    if not smtp_config or not recipients:
        logger.warning('[Email] Config or recipients missing')
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(title, 'utf-8')
        msg['From'] = smtp_config.get('from_addr', smtp_config.get('user', ''))
        msg['To'] = ', '.join(recipients)

        html_part = MIMEText(f'<h2>{title}</h2><p>{content}</p>', 'html', 'utf-8')
        msg.attach(html_part)

        use_tls = smtp_config.get('use_tls', True)
        if use_tls:
            server = smtplib.SMTP(smtp_config['host'], smtp_config.get('port', 587), timeout=5)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(smtp_config['host'], smtp_config.get('port', 25), timeout=5)

        if smtp_config.get('user') and smtp_config.get('password'):
            server.login(smtp_config['user'], smtp_config['password'])

        server.sendmail(msg['From'], recipients, msg.as_string())
        server.quit()
        logger.info(f'[Email] Sent to {recipients}')
        return True
    except smtplib.SMTPException as e:
        logger.error(f'[Email] SMTP error: {e}')
        return False


def notify_via_integration_hub(event_type: str, title: str, content: str, recipients: list) -> bool:
    """通过 Integration Hub 通道发送通知 (如果可用)

    尝试从 conf/env.py 读取集成配置，如果启用了 integration_hub 则通过它发送。
    否则 fallback 到直接 webhook。
    """
    try:
        from django.conf import settings
        hub_config = getattr(settings, 'INTEGRATION_HUB', None) or {}
        if not hub_config.get('enabled'):
            return False

        import requests
        payload = {
            'event': event_type,
            'title': title,
            'content': content,
            'recipients': recipients,
            'source': 'itsm',
        }
        resp = requests.post(
            hub_config.get('webhook_url', ''),
            json=payload,
            timeout=10,
        )
        if resp.ok:
            logger.info(f'[IntegrationHub] Notify sent: {event_type}')
            return True
        logger.warning(f'[IntegrationHub] Send failed: {resp.status_code}')
        return False
    except ImportError:
        return False
    except Exception as e:
        logger.warning(f'[IntegrationHub] Error: {e}')
        return False


def get_config_from_ticket(ticket, key, default=None):
    """从 ticket.meta 或 settings 中读取通知配置"""
    # Ticket-level config overrides global settings
    meta = ticket.meta or {}
    return meta.get(key, default)


# ========== NotificationService ==========

class NotificationService:
    """通知服务 — 发送工单状态通知"""

    # 通道优先级: 站内 > Integration Hub > 直接 webhook
    _channels = ['internal', 'integration_hub', 'wecom', 'dingtalk', 'email']

    @staticmethod
    def notify_state_enter(ticket, state_name, processors):
        """进入新节点时通知处理人"""
        if not processors:
            return
        message = f'工单 [{ticket.sn}] {ticket.title} 已进入 "{state_name}" 节点，请处理'
        NotificationService._send(ticket, message, processors, 'state_enter')

    @staticmethod
    def notify_approval(ticket, node_name, processors):
        """审批节点通知审批人"""
        if not processors:
            return
        message = f'您有新的审批任务: 工单 [{ticket.sn}] {ticket.title} 需要 "{node_name}" 审批'
        NotificationService._send(ticket, message, processors, 'approval')

    @staticmethod
    def notify_approved(ticket, node_name, operator):
        """审批通过通知"""
        message = f'工单 [{ticket.sn}] "{node_name}" 已被 {operator} 审批通过'
        NotificationService._send(ticket, message, [ticket.creator], 'approved')

    @staticmethod
    def notify_rejected(ticket, node_name, operator):
        """审批拒绝通知"""
        message = f'工单 [{ticket.sn}] "{node_name}" 被 {operator} 拒绝'
        NotificationService._send(ticket, message, [ticket.creator], 'rejected')

    @staticmethod
    def notify_sla_violation(ticket):
        """SLA 超时通知"""
        message = f'【SLA 超时】工单 [{ticket.sn}] {ticket.title} 已超过处理时限'
        NotificationService._send(ticket, message, [ticket.creator], 'sla_violation')

    @staticmethod
    def _send(ticket, message, recipients, event_type):
        """发送通知 — 遍历所有已配置的通道"""
        if not recipients:
            return
        try:
            recipients_list = recipients if isinstance(recipients, list) else [recipients]
            logger.info(f'[ITSM Notify] {event_type}: {message} -> {recipients_list}')

            # 1. 站内通知 (always)
            NotificationService._store_internal(ticket, message, recipients_list, event_type)

            # 2. 外部通道通知 (根据配置)
            meta = ticket.meta or {}
            title = f'ITSM {event_type} - {ticket.sn}'

            # Integration Hub (preferred)
            if notify_via_integration_hub(event_type, title, message, recipients_list):
                pass  # sent via hub

            # WeCom Robot
            wecom_webhook = get_config_from_ticket(ticket, 'wecom_webhook') or NotificationService._get_global_config('WECOM_WEBHOOK')
            if wecom_webhook:
                send_wecom_notify(wecom_webhook, title, message)

            # DingTalk Robot
            dingtalk_webhook = get_config_from_ticket(ticket, 'dingtalk_webhook') or NotificationService._get_global_config('DINGTALK_WEBHOOK')
            if dingtalk_webhook:
                send_dingtalk_notify(dingtalk_webhook, title, message)

        except Exception as e:
            logger.error(f'Failed to send notification: {e}')

    @staticmethod
    def _store_internal(ticket, message, recipients_list, event_type):
        """站内通知 — 存入 ticket.meta 供前端轮询"""
        try:
            meta = ticket.meta or {}
            notifications = meta.get('notifications', [])
            notifications.append({
                'event': event_type,
                'message': message,
                'recipients': recipients_list,
                'time': __import__('datetime').datetime.now().isoformat(),
            })
            meta['notifications'] = notifications[-50:]  # Keep last 50
            ticket.meta = meta
            ticket.save(update_fields=['meta'])
        except Exception as e:
            logger.error(f'Failed to store internal notification: {e}')

    @staticmethod
    def _get_global_config(key):
        """从 Django settings 读取全局配置"""
        try:
            from django.conf import settings
            return getattr(settings, key, None) or getattr(settings, 'ITSM_NOTIFY', {}).get(key)
        except Exception:
            return None

    @staticmethod
    def _get_smtp_config(ticket):
        """获取 SMTP 配置 — 先从工单 meta 取，fallback 到 settings"""
        meta = ticket.meta or {}
        smtp = meta.get('smtp_config')
        if smtp:
            return smtp
        try:
            from django.conf import settings
            default_smtp = getattr(settings, 'ITSM_NOTIFY', {}).get('SMTP')
            if default_smtp:
                return default_smtp
            # Fallback to Django's default email settings
            return {
                'host': getattr(settings, 'EMAIL_HOST', ''),
                'port': getattr(settings, 'EMAIL_PORT', 587),
                'user': getattr(settings, 'EMAIL_HOST_USER', ''),
                'password': getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
                'use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
                'from_addr': getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
            }
        except Exception:
            return None
