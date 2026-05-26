from django.apps import AppConfig


class OpsAgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opsagent'
    verbose_name = 'OpsAgent - LLM运维Agent'
