from django.apps import AppConfig


class ItsmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'itsm'
    verbose_name = 'ITSM 服务管理'

    def ready(self):
        """Register signal handlers"""
        try:
            from . import signals  # noqa
        except ImportError:
            pass
