# -*- coding: utf-8 -*-
"""ITSM Celery 定时任务

- sla_check: 每分钟检查活跃工单的 SLA 状态
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def sla_check():
    """SLA 定时检查 — 每分钟执行"""
    try:
        from itsm.services.sla_engine import SlaEngine
        result = SlaEngine.check_all_active_sla()
        if result['checked'] > 0:
            logger.info(f'SLA check: {result["checked"]} active, '
                        f'{result["warnings"]} warnings, {result["violations"]} violations')
        return result
    except Exception as e:
        logger.error(f'SLA check failed: {e}')
        return {'error': str(e)}


@shared_task
def auto_resolve_expired_tickets():
    """自动关闭超时未处理的草稿工单（每日执行）"""
    from datetime import timedelta
    from django.utils import timezone
    from itsm.models import Ticket

    cutoff = timezone.now() - timedelta(days=7)
    expired = Ticket.objects.filter(
        current_status='draft',
        create_datetime__lt=cutoff,
    )
    count = 0
    for ticket in expired:
        try:
            if ticket.pipeline_id:
                from itsm.services.itsm_engine import ITSMEngine
                ITSMEngine(ticket).revoke()
            else:
                ticket.set_status('terminated', 'system')
            count += 1
        except Exception as e:
            logger.warning('Auto-close ticket %s failed: %s', ticket.sn, e)
    if count:
        logger.info('Auto-closed %d expired draft tickets', count)
    return {'closed': count}
