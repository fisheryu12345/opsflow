# -*- coding: utf-8 -*-
"""Apps config for job_platform"""

from django.apps import AppConfig


class JobPlatformConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'job_platform'
    verbose_name = '作业平台'

    def ready(self):
        """应用启动时同步内置高危规则"""
        import logging
        logger = logging.getLogger(__name__)
        try:
            from .services.dangerous_detector import sync_builtin_rules
            sync_builtin_rules()
        except Exception as e:
            logger.warning(f"同步内置高危规则失败（可忽略）: {e}")
