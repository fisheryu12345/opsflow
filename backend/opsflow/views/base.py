"""ViewSet base class — project isolation + multi-tenant permission support

ProjectFilteredViewSet uses iam.resolvers for project-level data isolation.
BusinessMember inheritance is handled transparently — Business Admin/Editor
automatically see all projects under their business without needing explicit
ProjectMember records.
"""

from django.db.models import Q
from rest_framework import viewsets, exceptions
from rest_framework.permissions import IsAuthenticated
from iam.resolvers import get_visible_projects, has_project_role
from iam.permissions import TenantPermission


class ProjectFilteredViewSet(viewsets.ModelViewSet):
    """Project-scoped ViewSet with multi-tenant permission enforcement.

    - ?project_id=X  → narrows to that project, validates user access
    - no project_id  → returns resources from all user-visible projects
    - perform_create → auto-assigns project FK, validates user can create

    permission_classes default includes TenantPermission which enforces:
      - Write (PUT/PATCH/DELETE): user must have editor+ on the object's project
      - Read: queryset filtering handles visibility
    """
    project_field = 'project'  # model FK field name
    include_public = False     # set True to also return business-public templates

    def get_user_project_ids(self):
        """Return all project IDs visible to the current user.

        Uses iam.resolvers which combines direct ProjectMember records
        with inherited access from BusinessMember roles.
        """
        return get_visible_projects(self.request.user)

    def _add_public_q(self, q=None, project_id=None, user_project_ids=None):
        """When include_public=True, add public template visibility.

        Business-public: templates with project_scope containing specific
        project IDs. The '*' wildcard (platform-public) is no longer supported.
        """
        q = q or Q()
        if not self.include_public:
            return q
        if project_id is not None:
            return q | Q(is_public=True, project_scope__contains=str(project_id))
        # No specific project: return public templates visible to user's projects
        if user_project_ids:
            for pid in user_project_ids:
                q = q | Q(is_public=True, project_scope__contains=str(pid))
        return q

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            project_id = self.request.query_params.get('project_id')
            if project_id:
                base_q = Q(**{self.project_field + '_id': project_id})
                if self.include_public:
                    base_q |= Q(is_public=True)
                return qs.filter(base_q)
            return qs

        user_project_ids = self.get_user_project_ids()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            if int(project_id) not in user_project_ids:
                raise exceptions.PermissionDenied('No access to this project')
            base_q = Q(**{self.project_field + '_id': project_id})
            base_q = self._add_public_q(base_q, project_id=project_id)
            return qs.filter(base_q)
        base_q = Q(**{self.project_field + '__in': user_project_ids})
        base_q = self._add_public_q(base_q, user_project_ids=user_project_ids)
        return qs.filter(base_q)

    @staticmethod
    def resolve_project_kwargs(request, project_id=None):
        """Resolve project assignment for create operations.

        - project_id given → returns {'project_id': project_id}
        - no project_id   → returns {'project': first project} (backward compat)
        - callers should validate user permission separately
        """
        pid = project_id or request.query_params.get('project_id')
        if pid:
            return {'project_id': int(pid)}
        from iam.models import Project
        first = Project.objects.first()
        return {'project': first} if first else {}

    def perform_create(self, serializer):
        """Validate user can create in target project, then save."""
        kwargs = self.resolve_project_kwargs(self.request)
        if 'project_id' in kwargs:
            user_project_ids = self.get_user_project_ids()
            if kwargs['project_id'] not in user_project_ids:
                raise exceptions.PermissionDenied(
                    'No permission to create resources in this project'
                )
        serializer.save(**kwargs)


class ProjectReadOnlyViewSet(ProjectFilteredViewSet):
    """Read-only variant — disables all write operations."""
    def create(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)
    def update(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)
    def partial_update(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)
    def destroy(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)
