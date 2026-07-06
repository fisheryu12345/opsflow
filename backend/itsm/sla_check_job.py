# -*- coding: utf-8 -*-
"""SLA 定时检查任务（APScheduler 版）

替代 celery beat，与 opsflow/core/scheduler_service.py 保持一致模式。
"""

import logging

logger = logging.getLogger(__name__)


def sla_check_job():
    """SLA 定时检查 — 每分钟执行"""
    try:
        from itsm.services.sla_engine import SlaEngine
        result = SlaEngine.check_all_active_sla()
        if result['checked'] > 0:
            logger.info(
                'SLA check: %d active, %d warnings, %d violations',
                result['checked'], result['warnings'], result['violations'],
            )
        return result
    except Exception as e:
        logger.error('SLA check failed: %s', e)
        return {'error': str(e)}
