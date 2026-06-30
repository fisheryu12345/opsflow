from django.utils import timezone
from django.db import transaction, models
from rest_framework import mixins, viewsets, status, exceptions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from iam.models.menu_rbac import Role, Menu
from dvadmin.system.models import Users
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse, DetailResponse
from iam.models import (
    PermissionRequest, UserDirectPermission,
    BusinessGroup, Business, DeployEnvironment,
    BusinessMember, DeployEnvironmentPermission,
    Project, ProjectMember,
)
from iam.serializers import (
    PermissionRequestSerializer, PermissionRequestCreateSerializer,
    PermissionRequestReviewSerializer, UserDirectPermissionSerializer,
    BusinessGroupSerializer, BusinessSerializer, BusinessMemberSerializer,
    DeployEnvironmentSerializer, DeployEnvironmentPermissionSerializer,
    ProjectSerializerBase, ProjectMemberSerializer,
)


# ═══════════════════════════════════════════════════════════════════════════
# Permission Request Views (existing)
# ═══════════════════════════════════════════════════════════════════════════

class PermissionRequestViewSet(mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.ListModelMixin,
                               viewsets.GenericViewSet):
    queryset = PermissionRequest.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PermissionRequestCreateSerializer
        return PermissionRequestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(user=user)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        request_type_filter = self.request.query_params.get('request_type')
        if request_type_filter:
            qs = qs.filter(request_type=request_type_filter)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        permission_request = self.get_object()
        if not request.user.is_superuser:
            return ErrorResponse(msg='No permission')
        if permission_request.status != 'pending':
            return ErrorResponse(msg='Invalid status')
        ser = PermissionRequestReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            permission_request.status = 'approved'
            permission_request.reviewer = request.user
            permission_request.review_comment = ser.validated_data.get('review_comment', '')
            permission_request.reviewed_at = timezone.now()
            permission_request.save()
            if permission_request.request_type == 'role' and permission_request.target_role:
                permission_request.user.role.add(permission_request.target_role)
            elif permission_request.request_type == 'menu' and permission_request.target_menu:
                UserDirectPermission.objects.update_or_create(
                    user=permission_request.user, menu=permission_request.target_menu,
                    defaults={'granted_by': request.user})
            elif permission_request.request_type == 'menu_button' and permission_request.target_menu_button:
                UserDirectPermission.objects.update_or_create(
                    user=permission_request.user, menu_button=permission_request.target_menu_button,
                    defaults={'granted_by': request.user})
        return SuccessResponse(data=PermissionRequestSerializer(permission_request).data, msg='Approved')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        permission_request = self.get_object()
        if not request.user.is_superuser:
            return ErrorResponse(msg='No permission')
        if permission_request.status != 'pending':
            return ErrorResponse(msg='Invalid status')
        ser = PermissionRequestReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        permission_request.status = 'rejected'
        permission_request.reviewer = request.user
        permission_request.review_comment = ser.validated_data.get('review_comment', '')
        permission_request.reviewed_at = timezone.now()
        permission_request.save()
        return SuccessResponse(data=PermissionRequestSerializer(permission_request).data, msg='Rejected')

    @action(detail=False, methods=['get'])
    def available_roles(self, request):
        qs = Role.objects.filter(status=True).values('id', 'name')
        return SuccessResponse(data=list(qs))

    @action(detail=False, methods=['get'])
    def available_menus(self, request):
        qs = Menu.objects.filter(status=1, visible=1).values('id', 'name', 'parent', 'web_path')
        return SuccessResponse(data=list(qs))


class UserDirectPermissionViewSet(mixins.ListModelMixin,
                                   mixins.DestroyModelMixin,
                                   viewsets.GenericViewSet):
    queryset = UserDirectPermission.objects.all()
    serializer_class = UserDirectPermissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        return qs


# ═══════════════════════════════════════════════════════════════════════════
# BusinessGroup ViewSet
# ═══════════════════════════════════════════════════════════════════════════

class BusinessGroupViewSet(viewsets.ModelViewSet):
    """BusinessGroup CRUD — superuser only"""
    queryset = BusinessGroup.objects.all()
    serializer_class = BusinessGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_superuser:
            raise exceptions.PermissionDenied()
        return super().get_queryset()


# ═══════════════════════════════════════════════════════════════════════════
# Business ViewSet
# ═══════════════════════════════════════════════════════════════════════════

class BusinessViewSet(viewsets.ModelViewSet):
    """Business CRUD + member management"""
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()
        from iam.resolvers import get_visible_businesses
        visible_ids = get_visible_businesses(user)
        return super().get_queryset().filter(id__in=visible_ids)

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            raise exceptions.PermissionDenied()
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.is_superuser:
            raise exceptions.PermissionDenied()
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser:
            raise exceptions.PermissionDenied()
        if instance.projects.exists():
            raise exceptions.ValidationError('Business has projects, delete them first')
        instance.delete()

    # ── Member management ──────────────────────────────────────────

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        business = self.get_object()
        if request.method == 'GET':
            members = BusinessMember.objects.filter(business=business).select_related('user')
            ser = BusinessMemberSerializer(members, many=True)
            return SuccessResponse(data=ser.data)

        # POST: add member
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'editor')
        if not user_id:
            return ErrorResponse(msg='user_id required')
        _, created = BusinessMember.objects.get_or_create(
            business=business, user_id=user_id, defaults={'role': role})
        return DetailResponse(data={'created': created}, msg='Member added')

    @action(detail=True, methods=['delete'], url_path='members/(?P<member_id>[^/.]+)')
    def remove_member(self, request, pk=None, member_id=None):
        business = self.get_object()
        try:
            m = BusinessMember.objects.get(id=member_id, business=business)
            if m.user == request.user:
                return ErrorResponse(msg='Cannot remove yourself')
            m.delete()
            return SuccessResponse(data=None, msg='Member removed')
        except BusinessMember.DoesNotExist:
            return ErrorResponse(msg='Member not found', status=404)


# ═══════════════════════════════════════════════════════════════════════════
# DeployEnvironment ViewSet
# ═══════════════════════════════════════════════════════════════════════════

class DeployEnvironmentViewSet(viewsets.ModelViewSet):
    """DeployEnvironment CRUD + permission management — superuser for write"""
    queryset = DeployEnvironment.objects.all()
    serializer_class = DeployEnvironmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            raise exceptions.PermissionDenied()
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.is_superuser:
            raise exceptions.PermissionDenied()
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser:
            raise exceptions.PermissionDenied()
        instance.delete()

    @action(detail=True, methods=['get', 'post'], url_path='permissions')
    def permissions(self, request, pk=None):
        env = self.get_object()
        if request.method == 'GET':
            perms = DeployEnvironmentPermission.objects.filter(environment=env).select_related('user')
            ser = DeployEnvironmentPermissionSerializer(perms, many=True)
            return SuccessResponse(data=ser.data)

        # POST: grant permission
        user_id = request.data.get('user_id')
        if not user_id:
            return ErrorResponse(msg='user_id required')
        can_execute = request.data.get('can_execute', True)
        obj, created = DeployEnvironmentPermission.objects.update_or_create(
            user_id=user_id, environment=env,
            defaults={'can_execute': can_execute, 'granted_by': request.user})
        ser = DeployEnvironmentPermissionSerializer(obj)
        return DetailResponse(data=ser.data, msg='Permission granted' if created else 'Permission updated')

    @action(detail=True, methods=['delete'], url_path='permissions/(?P<perm_id>[^/.]+)')
    def revoke_permission(self, request, pk=None, perm_id=None):
        env = self.get_object()
        try:
            p = DeployEnvironmentPermission.objects.get(id=perm_id, environment=env)
            p.delete()
            return SuccessResponse(data=None, msg='Permission revoked')
        except DeployEnvironmentPermission.DoesNotExist:
            return ErrorResponse(msg='Permission not found', status=404)


# ═══════════════════════════════════════════════════════════════════════════
# Project ViewSet (iam-owned)
# ═══════════════════════════════════════════════════════════════════════════

class IamProjectViewSet(viewsets.ModelViewSet):
    """Project CRUD (iam-owned) — for admin panel use"""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializerBase
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()
        from iam.resolvers import get_visible_projects
        visible_ids = get_visible_projects(user)
        return super().get_queryset().filter(id__in=visible_ids)

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            raise exceptions.PermissionDenied()
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        project = self.get_object()
        if request.method == 'GET':
            members = ProjectMember.objects.filter(project=project).select_related('user')
            ser = ProjectMemberSerializer(members, many=True)
            return SuccessResponse(data=ser.data)

        user_id = request.data.get('user_id')
        role = request.data.get('role', 'editor')
        if not user_id:
            return ErrorResponse(msg='user_id required')
        _, created = ProjectMember.objects.get_or_create(
            project=project, user_id=user_id, defaults={'role': role})
        return DetailResponse(data={'created': created}, msg='Member added')

    @action(detail=True, methods=['delete'], url_path='members/(?P<member_id>[^/.]+)')
    def remove_member(self, request, pk=None, member_id=None):
        project = self.get_object()
        try:
            m = ProjectMember.objects.get(id=member_id, project=project)
            if m.user == request.user:
                return ErrorResponse(msg='Cannot remove yourself')
            m.delete()
            return SuccessResponse(data=None, msg='Member removed')
        except ProjectMember.DoesNotExist:
            return ErrorResponse(msg='Member not found', status=404)


# ═══════════════════════════════════════════════════════════════════════════
# User Search — 供审批原子 async_select 使用
# ═══════════════════════════════════════════════════════════════════════════


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    """搜索用户，返回 async_select 格式 {data: [{value: id, label: username}]}"""
    q = request.query_params.get('search', '').strip()
    users = Users.objects.filter(is_active=True)
    if q:
        users = users.filter(models.Q(username__icontains=q) | models.Q(name__icontains=q))
    users = users[:50]
    data = [{'value': u.id, 'label': f"{u.name or u.username} ({u.username})"}
            for u in users]
    return SuccessResponse(data=data)


# ═══════════════════════════════════════════════════════════════════════════
# My Permissions — 用户查看自己当前权限
# ═══════════════════════════════════════════════════════════════════════════

ITSM_PAGE_DEFS = [
    ('tickets', 'My Tickets', '我的工单'),
    ('workflows', 'Workflow Templates', '流程模板'),
    ('incidents', 'Incidents', '事件'),
    ('changes', 'Changes', '变更'),
    ('sla', 'SLA Policies', 'SLA'),
    ('delegation', 'Delegation', '委托'),
    ('dashboard', 'Dashboard', '看板'),
    ('team-dashboard', 'Team Dashboard', '团队看板'),
    # editor+
    ('skill-groups', 'Skill Groups', '技能组'),
    ('on-duty', 'On-Duty Schedule', '排班'),
    # admin only
    ('assign-rules', 'Assign Rules', '路由'),
    ('escalation', 'Escalation Levels', '升级'),
]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_permissions(request):
    """Return current user's ITSM permissions for a given project."""
    project_id = request.query_params.get('project_id')
    if not project_id:
        return ErrorResponse(msg='project_id required')

    try:
        project_id = int(project_id)
    except (ValueError, TypeError):
        return ErrorResponse(msg='project_id must be an integer')

    user = request.user

    # Determine IAM role on this project
    from iam.resolvers import ROLE_ORDER
    role = 'viewer'
    try:
        pm = ProjectMember.objects.filter(project_id=project_id, user=user).first()
        if pm:
            role = pm.role
        else:
            # Check BusinessMember inheritance
            project = Project.objects.only('business_id').get(id=project_id)
            if project.business_id:
                bm = BusinessMember.objects.filter(
                    business_id=project.business_id, user=user
                ).first()
                if bm:
                    role = bm.role
    except Project.DoesNotExist:
        return ErrorResponse(msg='Project not found', status=404)

    # Determine visible pages
    is_admin = role == 'admin'
    is_editor = role == 'editor'
    pages = []
    for key, label_en, label_zh in ITSM_PAGE_DEFS:
        visible = True
        if key in ('skill-groups', 'on-duty'):
            visible = is_admin or is_editor
        elif key in ('assign-rules', 'escalation'):
            visible = is_admin
        pages.append({'key': key, 'label_en': label_en, 'label_zh': label_zh, 'visible': visible})

    # Collect dvadmin permission keys for ITSM
    perm_keys = set()
    if user.is_superuser:
        # Superuser: return all ITSM permissions
        from iam.models.menu_rbac import MenuButton
        perm_keys = set(MenuButton.objects.filter(
            value__startswith='itsm:'
        ).values_list('value', flat=True))
    else:
        # Get permission keys from user's dvadmin Roles
        for r in user.role.filter(status=1):
            for mbp in r.role_menu_button.select_related('menu_button').all():
                if mbp.menu_button and mbp.menu_button.value.startswith('itsm:'):
                    perm_keys.add(mbp.menu_button.value)
        # Also check UserDirectPermission
        for dp in UserDirectPermission.objects.filter(user=user).select_related('menu_button'):
            if dp.menu_button and dp.menu_button.value.startswith('itsm:'):
                perm_keys.add(dp.menu_button.value)

    return DetailResponse(data={
        'role': role,
        'project_id': project_id,
        'pages': pages,
        'permissions': sorted(perm_keys),
    })
