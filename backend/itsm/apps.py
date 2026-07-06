import logging
import os

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

        # Register and start SLA periodic check via APScheduler (dev mode only)
        if os.environ.get('RUN_MAIN') or os.environ.get('DJANGO_AUTORELOAD'):
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
                scheduler.start()
                # Keep reference to prevent GC
                self._sla_scheduler = scheduler
                logger.info('[ITSM] SLA check scheduler started')
            except Exception:
                logger.warning('[ITSM] APScheduler not available, SLA check will not auto-run')
