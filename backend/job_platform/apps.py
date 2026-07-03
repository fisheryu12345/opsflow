# -*- coding: utf-8 -*-
"""Apps config for job_platform"""

from django.apps import AppConfig


class JobPlatformConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'job_platform'
    verbose_name = '作业平台'

    def ready(self):
        """预留 — 种子数据移至 seed_job_platform 命令"""
        pass
