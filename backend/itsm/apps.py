import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ItsmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'itsm'
    verbose_name = 'ITSM 服务管理'

    def ready(self):
        """Register signal handlers, pipeline components, and APScheduler jobs"""
        try:
            from . import signals  # noqa
        except ImportError:
            pass
        try:
            from .pipeline_plugins import components  # noqa — register ITSM components with ComponentLibrary
        except ImportError:
            pass

        # Register and start APScheduler jobs
        # Skip only the Django dev reloader parent process (where RUN_MAIN is absent).
        # In production (no reloader) and dev child process (RUN_MAIN='true'), start.
        # Set DISABLE_ITSM_SCHEDULER=1 to suppress in multi-worker deployments.
        is_reloader_parent = os.environ.get('RUN_MAIN') != 'true' and 'runserver' in sys.argv
        if not is_reloader_parent and os.environ.get('DISABLE_ITSM_SCHEDULER') != '1':
            try:
                from django.conf import settings
                from apscheduler.schedulers.background import BackgroundScheduler
                from apscheduler.triggers.interval import IntervalTrigger
                from itsm.sla_check_job import sla_check_job

                tz = getattr(settings, 'TIME_ZONE', 'Asia/Shanghai')
                scheduler = BackgroundScheduler(timezone=tz)
                scheduler.add_job(
                    sla_check_job,
                    trigger=IntervalTrigger(seconds=60),
                    id='itsm_sla_check',
                    name='SLA check',
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                    misfire_grace_time=30,
                )
                # Trigger executor: process PENDING executions every 10s
                from itsm.services.trigger_service import TriggerExecutor
                scheduler.add_job(
                    TriggerExecutor.process_pending,
                    trigger=IntervalTrigger(seconds=10),
                    id='itsm_trigger_executor',
                    name='Trigger executor',
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                    misfire_grace_time=5,
                )
                # Trigger cleanup: delete executions older than 365 days
                scheduler.add_job(
                    TriggerExecutor.cleanup_old_executions,
                    trigger=IntervalTrigger(days=1),
                    id='itsm_trigger_cleanup',
                    name='Trigger execution cleanup',
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                    misfire_grace_time=3600,
                )
                scheduler.start()
                # Keep reference to prevent GC
                self._sla_scheduler = scheduler
                logger.info('[ITSM] SLA check + trigger scheduler started')
            except Exception:
                logger.warning('[ITSM] APScheduler not available, SLA check will not auto-run')
