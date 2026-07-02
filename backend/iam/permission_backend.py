"""Unified DRF permission backend — replaces dvadmin CustomPermission

Usage:
    class MyViewSet(ModelViewSet):
        permission_classes = [IAMPermissionBackend]
        required_permission = 'system:user:manage'

        @action(methods=['POST'], detail=False, required_permission='opsflow:template:create')
        def create(self, request, *args, **kwargs):
            ...
"""
from rest_framework.permissions import BasePermission

from iam.models import IAMPermission, IAMUserRole
from iam.models.rbac import UserDirectPermission
from iam.resolvers import has_project_role, get_project_role
from iam.models.permission import IAMRolePermission


ROLE_ORDER = {'viewer': 0, 'editor': 1, 'admin': 2}


def _meets_min_role(user_role: str | None, min_role: str | None) -> bool:
    """Check if user's project role meets the minimum requirement."""
    if not min_role:
        return True
    return ROLE_ORDER.get(user_role, -1) >= ROLE_ORDER.get(min_role, 0)


class IAMPermissionChecker:
    """Single entry point for all permission checks."""

    @staticmethod
    def has_perm(user, codename, request=None):
        """Does the user have this codename permission?"""
        try:
            perm = IAMPermission.objects.get(codename=codename)
        except IAMPermission.DoesNotExist:
            return False

        if user.is_superuser:
            return True

        # Check direct permission grants
        if UserDirectPermission.objects.filter(
            user=user, permission__codename=codename
        ).exists():
            return True

        # Check role-based permission
        role_perm = IAMRolePermission.objects.filter(
            role__user_roles__user=user.id,
            permission__codename=codename,
        ).first()
        if not role_perm:
            return False

        # Platform-scoped: pass through
        if perm.scope == 'platform':
            return True

        # Project-scoped: check project role
        project_id = request.query_params.get('project_id') if request else None
        if not project_id:
            return False
        user_role = get_project_role(user, project_id)
        return _meets_min_role(user_role, role_perm.min_project_role)

    @staticmethod
    def has_any_perm(user, app: str) -> bool:
        """Does the user have ANY permission in the given app?"""
        if user.is_superuser:
            return True
        # Direct permissions
        if UserDirectPermission.objects.filter(
            user=user, permission__app=app
        ).exists():
            return True
        # Role-based permissions
        if IAMRolePermission.objects.filter(
            role__user_roles__user=user.id,
            permission__app=app,
        ).exists():
            return True
        return False


class IAMPermissionBackend(BasePermission):
    """Unified DRF permission backend for all sub-products."""

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        # Check action-specific permission first (dict mapping action → codename)
        action_perms = getattr(view, 'action_permissions', {})
        perm = action_perms.get(view.action)
        if not perm:
            # Fall back to class-level required_permission
            perm = getattr(view, 'required_permission', None)
        if not perm:
            return True
        return IAMPermissionChecker.has_perm(request.user, perm, request)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if request.method in ('PUT', 'PATCH', 'DELETE'):
            project_id = getattr(obj, 'project_id', None)
            if project_id:
                return has_project_role(request.user, project_id, 'editor')
        return True
