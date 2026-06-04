# -*- coding: utf-8 -*-
"""AppConfig for monitor app"""

from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'
    verbose_name = '监控告警中心'
