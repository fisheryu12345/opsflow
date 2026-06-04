# -*- coding: utf-8 -*-
"""AppConfig for integration app"""

from django.apps import AppConfig


class IntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'integration'
    verbose_name = '集成中心 (Integration Hub)'
