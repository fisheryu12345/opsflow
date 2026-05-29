from django.apps import AppConfig


class OpsflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opsflow'
    verbose_name = 'OpsFlow - 运维编排平台'

    def ready(self):
        from opsflow.core.atom_registry import scan_atoms
        scan_atoms()
        from opsflow.core.atom_service import register_atom_services
        register_atom_services()
