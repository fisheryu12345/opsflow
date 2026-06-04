# -*- coding: utf-8 -*-
"""AppConfig for itsm app"""

from django.apps import AppConfig


class ItsmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'itsm'
    verbose_name = 'ITSM 服务管理'
