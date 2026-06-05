# -*- coding: utf-8 -*-
"""AppConfig for monitor app — 启动 MonitorScheduler"""

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'
    verbose_name = '监控告警中心'

    def ready(self):
        """Django 启动时自动初始化 MonitorScheduler"""
        import os
        if os.environ.get('RUN_MAIN') or os.environ.get('DJANGO_AUTORELOAD'):
            try:
                from .services.scheduler import MonitorScheduler
                scheduler = MonitorScheduler()
                scheduler.start()
                # 保存引用防止 GC
                self.monitor_scheduler = scheduler
                logger.info("[Monitor] MonitorScheduler 已自动启动")
            except Exception as e:
                logger.warning(f"[Monitor] MonitorScheduler 启动失败: {e}")
