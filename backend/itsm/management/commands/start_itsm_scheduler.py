# -*- coding: utf-8 -*-
"""ITSM 调度器 — 独立进程，用于工单升级检测等定时任务

启动方式: python manage.py start_itsm_scheduler
"""

import logging
import time

from django.core.management.base import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)

# ITSM 所有 APScheduler job_id 前缀
JOB_PREFIX = 'itsm_'


def escalation_check():
    """工单升级检测 — 每分钟执行"""
    from itsm.services.escalation_service import EscalationService
    EscalationService.check_and_escalate()


class ItsmScheduler:
    """ITSM 独立 APScheduler 实例"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        self.scheduler.add_jobstore(DjangoJobStore(), 'default')
        self._started = False

    def start(self):
        if self._started:
            return
        self._register_jobs()
        self.scheduler.start()
        self._started = True
        logger.info("ItsmScheduler started")

    def _register_jobs(self):
        self.scheduler.add_job(
            escalation_check,
            trigger=IntervalTrigger(seconds=60),
            id=JOB_PREFIX + 'escalation_check',
            name='工单升级检测',
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=30,
        )
        logger.info("[itsm_scheduler] escalation_check registered (interval=60s)")

    def shutdown(self, wait=False):
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("ItsmScheduler shut down")


itsm_scheduler = ItsmScheduler()


class Command(BaseCommand):
    help = '启动 ITSM 调度器（独立进程，与 OpsFlow 调度器隔离）'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('正在启动 ITSM 调度器...'))

        # Redis 锁防重复启动
        try:
            import redis
            from django.conf import settings
            r = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', '127.0.0.1'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
            )
            lock_key = 'lock:itsm_scheduler'
            if not r.set(lock_key, '1', nx=True, ex=60):
                self.stdout.write(self.style.WARNING('ITSM 调度器已在运行中（持有锁），退出'))
                return
        except Exception as e:
            logger.warning("Redis 锁检查失败（调度器仍将启动）: %s", e)

        itsm_scheduler.start()
        self.stdout.write(self.style.SUCCESS('ITSM 调度器已启动'))

        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            itsm_scheduler.shutdown()
            self.stdout.write(self.style.SUCCESS('ITSM 调度器已停止'))
