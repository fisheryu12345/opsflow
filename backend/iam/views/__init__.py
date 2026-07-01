"""IAM views package — RBAC + permission management views.

All views are importable from iam.views, preserving backward compatibility.
"""

from iam.views.permission_views import (
    PermissionRequestViewSet,
    UserDirectPermissionViewSet,
    BusinessGroupViewSet,
    BusinessViewSet,
    DeployEnvironmentViewSet,
    IamProjectViewSet,
    search_users,
    my_permissions,
    my_full_permissions,
    page_permissions,
    permission_catalog,
)
from iam.views.role import RoleViewSet
from iam.views.menu import MenuViewSet

__all__ = [
    'PermissionRequestViewSet',
    'UserDirectPermissionViewSet',
    'BusinessGroupViewSet',
    'BusinessViewSet',
    'DeployEnvironmentViewSet',
    'IamProjectViewSet',
    'search_users',
    'my_permissions',
    'my_full_permissions',
    'page_permissions',
    'RoleViewSet',
    'MenuViewSet',
]
