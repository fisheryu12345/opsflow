# -*- coding: utf-8 -*-
"""MonitorScheduler — 监控告警中心调度器

APScheduler 独立实例，管理所有 monitor 的后台任务。
"""

import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)
FSM = 'monitor_scheduler'


class MonitorScheduler:
    """监控告警中心调度器 — 独立于 OpsflowScheduler"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._running = False

    def start(self):
        """注册所有定时任务并启动"""
        if self._running:
            return
        self._register_jobs()
        self.scheduler.start()
        self._running = True
        logger.info("[MonitorScheduler] 已启动")

    def _register_jobs(self):
        """注册所有周期性任务"""
        # 1. 告警升级检查 (60s)
        self.scheduler.add_job(
            self._check_escalation,
            IntervalTrigger(seconds=60),
            id='monitor_escalation_check',
            replace_existing=True,
        )

        # 2. 静默/屏蔽生效检查 (60s)
        self.scheduler.add_job(
            self._check_shield,
            IntervalTrigger(seconds=60),
            id='monitor_shield_check',
            replace_existing=True,
        )

        # 3. 自动恢复检测 (300s)
        self.scheduler.add_job(
            self._auto_resolve,
            IntervalTrigger(seconds=300),
            id='monitor_auto_resolve',
            replace_existing=True,
        )

        # 4. 过期事件清理 (3600s)
        self.scheduler.add_job(
            self._clean_old_events,
            IntervalTrigger(seconds=3600),
            id='monitor_event_cleanup',
            replace_existing=True,
        )

    def _check_escalation(self):
        """检查需要升级的告警"""
        from ..models import Alert
        now = timezone.now()
        escalated = Alert.objects.filter(
            status__in=('firing', 'acknowledged'),
            next_escalate_at__lte=now,
        ).update(
            escalation_count=models.F('escalation_count') + 1,
            next_escalate_at=now + timedelta(hours=1),
        )
        if escalated:
            logger.info(f"[MonitorScheduler] 升级 {escalated} 条告警")
        return escalated

    def _check_shield(self):
        """检查新生效的屏蔽计划"""
        from ..models import ShieldPlan
        # 刷新屏蔽缓存
        count = ShieldPlan.objects.filter(is_enabled=True).count()
        logger.debug(f"[MonitorScheduler] 屏蔽计划生效中: {count} 条")

    def _auto_resolve(self):
        """自动恢复超时告警"""
        from ..models import Alert
        from django.db import models
        resolved = Alert.objects.filter(
            status='firing',
            strategy__isnull=False,
        )[:0]  # 简化版: 暂不自动恢复
        return 0

    def _clean_old_events(self):
        """清理过期 AlertEvent"""
        from ..models import AlertEvent
        cutoff = timezone.now() - timedelta(days=30)
        cnt, _ = AlertEvent.objects.filter(
            status='closed', time__lt=cutoff,
        ).delete()
        if cnt:
            logger.info(f"[MonitorScheduler] 清理 {cnt} 条过期事件")

    def stop(self):
        """停止调度器"""
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("[MonitorScheduler] 已停止")

    def __repr__(self):
        return f"<MonitorScheduler running={self._running}>"
