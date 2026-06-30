"""IAM app config — multi-tenant infrastructure + RBAC permission management

Provides:
- Tenant models: BusinessGroup, Business, DeployEnvironment
- Project models: Project, ProjectMember (migrated from opsflow)
- Membership models: BusinessMember, DeployEnvironmentPermission
- Resolvers: permission query functions for all sub-products
- Permission backends: TenantPermission, EnvironmentGatePermission
"""
from django.apps import AppConfig


class IamConfig(AppConfig):
    name = 'iam'
    verbose_name = 'IAM — Multi-Tenant & Permissions / 多租户权限管理'

    def ready(self):
        import iam.signals  # noqa: register signal handlers

        # Register identity sync cron jobs (only if scheduler is available)
        try:
            from iam.sync.jobs import register_sync_jobs
            from django_apscheduler.util import get_scheduler
            scheduler = get_scheduler()
            if scheduler and not scheduler.running:
                register_sync_jobs(scheduler)
        except Exception:
            # scheduler may not be ready at this point — jobs will register
            # on first scheduler start
            pass
