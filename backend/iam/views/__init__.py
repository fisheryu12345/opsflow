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
)
from iam.views.role import RoleViewSet
from iam.views.menu import MenuViewSet
from iam.views.menu_button import MenuButtonViewSet
from iam.views.menu_field import MenuFieldViewSet
from iam.views.role_menu import RoleMenuPermissionViewSet
from iam.views.role_menu_button_permission import RoleMenuButtonPermissionViewSet

__all__ = [
    # Permission views
    'PermissionRequestViewSet',
    'UserDirectPermissionViewSet',
    'BusinessGroupViewSet',
    'BusinessViewSet',
    'DeployEnvironmentViewSet',
    'IamProjectViewSet',
    'search_users',
    'my_permissions',
    # RBAC views (migrated from dvadmin)
    'RoleViewSet',
    'MenuViewSet',
    'MenuButtonViewSet',
    'MenuFieldViewSet',
    'RoleMenuPermissionViewSet',
    'RoleMenuButtonPermissionViewSet',
]
