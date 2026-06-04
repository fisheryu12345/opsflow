# -*- coding: utf-8 -*-
"""ITSM 通知服务 — 状态变更时的消息通知

支持的通知方式:
  - 站内通知 (WebSocket)
  - 后续可扩展: 邮件、企业微信、钉钉
"""

import json
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务 — 发送工单状态通知"""

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
        """发送通知（当前实现: 日志 + 写入 ticket.meta）"""
        if not recipients:
            return
        try:
            recipients_list = recipients if isinstance(recipients, list) else [recipients]
            logger.info(f'[ITSM Notify] {event_type}: {message} → {recipients_list}')
            # Store in ticket meta for front-end polling
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
            logger.error(f'Failed to send notification: {e}')
