from django.apps import AppConfig


class ItsmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'itsm'
    verbose_name = 'ITSM 服务管理'

    def ready(self):
        """Register signal handlers and pipeline components"""
        try:
            from . import signals  # noqa
        except ImportError:
            pass
        try:
            from .pipeline_plugins import components  # noqa — register ITSM components with ComponentLibrary
        except ImportError:
            pass
