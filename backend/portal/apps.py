# -*- coding: utf-8 -*-
"""Portal — 运维门户/个人工作台

轻后端，主要提供聚合查询接口，前端为主。
"""

from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portal'
    verbose_name = '运维门户'
