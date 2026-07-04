# -*- coding: utf-8 -*-
"""ITSM 信号处理器 — 工单状态变更时自动触发 SLA/通知 + post_set_state 同步"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from pipeline.eri.signals import post_set_state
from bamboo_engine import states

logger = logging.getLogger(__name__)


@receiver(post_save, sender='itsm.Ticket')
def ticket_post_save(sender, instance, created, **kwargs):
    """工单保存后 — 根据状态变化触发 SLA"""
    if created:
        return
    try:
        current = instance.current_status
        from itsm.services.sla_engine import SlaEngine
        if current == 'suspended':
            SlaEngine.pause_ticket_sla(instance)
        elif current == 'running':
            SlaEngine.resume_ticket_sla(instance)
        elif current in ('finished', 'terminated', 'failed'):
            SlaEngine.stop_ticket_sla(instance)
    except Exception as e:
        logger.warning(f'SLA signal error: {e}')


@receiver(post_set_state)
def itsm_post_set_state_handler(sender, node_id, to_state, version, root_id, **kwargs):
    """监听 bamboo 节点状态变更 → 同步 ITSM 工单状态

    非 ITSM 工单的 pipeline（如 OpsFlow）会安静跳过。
    """
    pipeline_id = root_id or node_id
    from itsm.models import Ticket
    try:
        ticket = Ticket.objects.get(pipeline_id=pipeline_id)
    except Ticket.DoesNotExist:
        return  # 不是 ITSM 工单 pipeline，安静跳过

    # 更新节点状态快照
    node_status = dict(ticket.node_status or {})
    # bamboo 状态 → ITSM 语义映射
    status_map = {
        states.READY: 'pending',
        states.RUNNING: 'running',
        states.FINISHED: 'finished',
        states.FAILED: 'failed',
        states.SUSPENDED: 'suspended',
        states.REVOKED: 'cancelled',
        states.BLOCKED: 'blocked',
    }
    mapped = status_map.get(to_state, to_state)
    node_status[node_id] = mapped
    ticket.node_status = node_status

    # 更新 TicketStatus（含 SLA 启动）
    if to_state == states.RUNNING:
        ticket.state_history = list(ticket.state_history or []) + [{
            'state_id': node_id,
            'status': 'running',
            'timestamp': str(ticket.update_datetime or ticket.create_datetime),
        }]

    ticket.save(update_fields=['node_status', 'state_history'])

    # 节点进入时触发 SLA 启动
    if to_state == states.RUNNING:
        from itsm.services.sla_engine import SlaEngine
        try:
            SlaEngine.start_ticket_sla(ticket)
        except Exception as e:
            logger.warning('[Signal] SLA start error for ticket %s: %s', ticket.id, e)
