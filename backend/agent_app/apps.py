# -*- coding: utf-8 -*-
"""AppConfig for agent app"""

from django.apps import AppConfig


class AgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agent_app'
    verbose_name = 'Agent 管理 (Agent)'
