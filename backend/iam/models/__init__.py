"""IAM app models — multi-tenant infrastructure + RBAC permission requests

All models are importable from iam.models, preserving backward compatibility
with existing code that references iam.models.PermissionRequest etc.
"""

from iam.models.rbac import PermissionRequest, UserDirectPermission
from iam.models.role_template import RoleTemplate
from iam.models.menu_rbac import (
    Role, Menu, MenuButton, MenuField, FieldPermission,
    RoleMenuPermission, RoleMenuButtonPermission,
)
from iam.models.tenant import BusinessGroup, Business, DeployEnvironment
from iam.models.project import Project, ProjectMember
from iam.models.membership import BusinessMember, DeployEnvironmentPermission

__all__ = [
    # RBAC (existing)
    'PermissionRequest',
    'UserDirectPermission',
    # RBAC (templates)
    'RoleTemplate',
    # RBAC (migrated from dvadmin)
    'Role',
    'Menu',
    'MenuButton',
    'MenuField',
    'FieldPermission',
    'RoleMenuPermission',
    'RoleMenuButtonPermission',
    # Tenant
    'BusinessGroup',
    'Business',
    'DeployEnvironment',
    # Project (migrated from opsflow)
    'Project',
    'ProjectMember',
    # Membership
    'BusinessMember',
    'DeployEnvironmentPermission',
]
