# -*- coding: utf-8 -*-
"""ITSM 信号处理器 — 工单状态变更时自动触发 SLA/通知"""

import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

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
