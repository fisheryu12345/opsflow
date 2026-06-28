"""DRF Permission Backends for multi-tenant access control.

These backends are used by all sub-product ViewSets to enforce:
- TenantPermission: user must have appropriate Project/Business role
- EnvironmentGatePermission: user must have explicit environment execution permission

Usage:
    from iam.permissions import TenantPermission, EnvironmentGatePermission

    class MyViewSet(ProjectFilteredViewSet):
        permission_classes = [IsAuthenticated, TenantPermission]
"""

from rest_framework.permissions import BasePermission
from iam.resolvers import has_project_role, can_execute_in_environment


class TenantPermission(BasePermission):
    """Unified multi-tenant permission check for all sub-product ViewSets.

    - Read (GET/HEAD/OPTIONS): authenticated users can read resources
      they can see (queryset filtering handles visibility)
    - Write (PUT/PATCH/DELETE): user must have at least Editor role
      on the resource's project
    - Create (POST): handled by ViewSet.perform_create() which validates
      the user belongs to the target project
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in ('PUT', 'PATCH', 'DELETE'):
            # obj must have a 'project_id' attribute
            project_id = getattr(obj, 'project_id', None)
            if project_id is None:
                return True  # No project = no restriction (e.g. public templates)
            return has_project_role(request.user, project_id, min_role='editor')
        return True


class EnvironmentGatePermission(BasePermission):
    """Environment gate for execution / ticket creation endpoints.

    Expects `environment_id` and optionally `project_id` in request data.
    Rejects requests where the user lacks explicit execution permission
    for the target environment.

    Usage: Add to ViewSet permission_classes for execution-related actions.
    """

    def has_permission(self, request, view):
        env_id = request.data.get('environment_id')
        if env_id is None:
            env_id = request.query_params.get('environment_id')

        if env_id is not None:
            project_id = request.data.get('project_id')
            if project_id is None:
                project_id = request.query_params.get('project_id')

            project_id = int(project_id) if project_id else None
            return can_execute_in_environment(
                request.user, int(env_id), project_id
            )

        # If no environment_id specified, allow — execution will be
        # constrained downstream. This handles backward compat with
        # existing API calls that don't yet pass environment_id.
        return True
