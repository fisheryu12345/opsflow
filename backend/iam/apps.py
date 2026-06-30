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
