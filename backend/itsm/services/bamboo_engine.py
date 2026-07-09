# -*- coding: utf-8 -*-
"""Bamboo Engine shared utilities — ITSM hosted, also used by Opsflow.
Extracts duplicate static methods from ITSMEngine and FlowEngine.
"""
import logging

from bamboo_engine import api as pipeline_api
from pipeline.eri.models import Schedule
from pipeline.eri.runtime import BambooDjangoRuntime

logger = logging.getLogger(__name__)


def activity_callback(activity_id, callback_data):
    """Send node callback to bamboo-engine (approval/fill-form done).

    Looks up the latest unfinished Schedule for version parameter.
    """
    try:
        schedule = Schedule.objects.filter(
            node_id=activity_id, finished=False
        ).order_by('-schedule_times').first()
        if not schedule:
            all_scheds = list(Schedule.objects.filter(finished=False).values_list('node_id', flat=True)[:20])
            logger.error('[BambooEngine] No active schedule for node %s, active(20): %s', activity_id, all_scheds)
            return False
        runtime = BambooDjangoRuntime()
        result = pipeline_api.callback(
            runtime, activity_id, schedule.version, callback_data
        )
        if not result.result:
            logger.error(
                '[BambooEngine] activity_callback failed: %s', result.message
            )
        return result.result
    except Exception as e:
        logger.error('[BambooEngine] activity_callback error: %s', e)
        return False


def revoke_by_pipeline_id(pipeline_id):
    """Revoke pipeline directly (for callers without ticket/execution reference)."""
    runtime = BambooDjangoRuntime()
    result = pipeline_api.revoke_pipeline(runtime, pipeline_id)
    if not result.result:
        logger.error('[BambooEngine] revoke_by_pipeline_id failed: %s', result.message)
    return result.result
