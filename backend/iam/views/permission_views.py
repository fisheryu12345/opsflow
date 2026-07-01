"""IAM permission views — PermissionRequest, DirectPermission, Business, Project, etc."""
from django.utils import timezone
from django.db import transaction, models
from rest_framework import mixins, viewsets, status, exceptions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from iam.models.page_config import IAMMenu
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

def _notify_user(user, action: str, req: 'PermissionRequest'):
    """Send in-app notification for permission request result."""
    try:
        from dvadmin.system.models import MessageCenter, MessageCenterTargetUser
        if action == 'approved':
            title = f"权限申请已通过 - Permission Approved"
            content = f"项目 [{req.target_project.name if req.target_project else '-'}] {req.get_target_project_role_display() if req.target_project_role else ''} 已获批" # pyright: ignore[reportAttributeAccessIssue]
        else:
            title = f"权限申请已拒绝 - Permission Rejected"
            content = f"项目 [{req.target_project.name if req.target_project else '-'}] 申请已拒绝。原因: {req.review_comment or '无'}"
        msg = MessageCenter.objects.create(title=title, content=content)
        MessageCenterTargetUser.objects.create(messagecenter=msg, users=user)
    except Exception:
        pass  # Non-blocking


def _notify_approvers(req: 'PermissionRequest'):
    """Send in-app notification to all potential approvers when a new request is submitted."""
    try:
        from dvadmin.system.models import MessageCenter, MessageCenterTargetUser, Users

        # Collect unique approver IDs (exclude requester to avoid duplicate notifications)
        approver_ids = set()

        # 1. All superusers can approve any request type
        for uid in Users.objects.filter(is_superuser=True).values_list('id', flat=True):
            approver_ids.add(uid)

        # 2. For project_role, also notify Business Admins of the target project's Business
        if req.request_type == 'project_role' and req.target_project is not None:
            from iam.models.membership import BusinessMember
            # Traverse BusinessMember → Business → Project via ORM to avoid FK _id fields
            project_pk = req.target_project.pk
            for uid in BusinessMember.objects.filter(
                role='admin', business__projects__id=project_pk
            ).values_list('user_id', flat=True):
                approver_ids.add(uid)

        # Remove the requester from approvers (no self-notification)
        if req.user:
            approver_ids.discard(req.user.pk)

        # Build notification content
        user_display = req.user.name or req.user.username

        # Map request_type to display label
        request_type_label = req.get_request_type_display() # pyright: ignore[reportAttributeAccessIssue]

        # Map target_project_role to display label (Pyright: get_FOO_display is runtime-generated)
        role_display = ''
        if req.target_project_role:
            for val, label in PermissionRequest.PROJECT_ROLE_CHOICES:
                if val == req.target_project_role:
                    role_display = label
                    break

        if req.request_type == 'project_role' and req.target_project:
            detail = f"项目 [{req.target_project.name}] {role_display}"
        elif req.request_type == 'role' and req.target_iam_role:
            detail = f"产品角色 [{req.target_iam_role.name}]"
        elif req.request_type == 'menu' and req.target_menu:
            detail = f"菜单 [{req.target_menu.name}]"
        elif req.request_type == 'menu_button':
            detail = f"按钮ID [{req.target_menu_button}]"
        else:
            detail = req.reason[:50] if req.reason else '-'

        # ── 1) Send submission confirmation to the requester ──
        confirm_title = "权限申请已提交 - Request Submitted"
        confirm_content = f"您的{request_type_label}权限申请已提交，等待审批。\n申请内容：{detail}\n理由：{req.reason or '无'}"
        confirm_msg = MessageCenter.objects.create(title=confirm_title, content=confirm_content)
        MessageCenterTargetUser.objects.create(messagecenter=confirm_msg, users=req.user)

        # ── 2) Notify all approvers ──
        if approver_ids:
            title = "新的权限申请 - New Permission Request"
            content = (
                f"用户 {user_display} 提交了{request_type_label}权限申请：{detail}。"
                f"理由：{req.reason or '无'}"
            )
            for uid in approver_ids:
                msg = MessageCenter.objects.create(title=title, content=content)
                MessageCenterTargetUser.objects.create(messagecenter=msg, users_id=uid)
    except Exception:
        pass  # Non-blocking


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
        req = serializer.save(user=self.request.user)
        _notify_approvers(req)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        permission_request = self.get_object()
        if permission_request.status != 'pending':
            return ErrorResponse(msg='Invalid status')

        # 审批权限：superuser OR 目标项目的 Business Admin
        if not request.user.is_superuser:
            if permission_request.request_type == 'project_role' and permission_request.target_project:
                from iam.resolvers import has_business_role
                if not has_business_role(request.user, permission_request.target_project.business_id, 'admin'):
                    return ErrorResponse(msg='No permission')
            else:
                return ErrorResponse(msg='No permission')

        ser = PermissionRequestReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            permission_request.status = 'approved'
            permission_request.reviewer = request.user
            permission_request.review_comment = ser.validated_data.get('review_comment', '')
            permission_request.reviewed_at = timezone.now()
            permission_request.save()

            if permission_request.request_type == 'role' and permission_request.target_iam_role:
                    from iam.models.permission import IAMUserRole
                    IAMUserRole.objects.get_or_create(
                        user=permission_request.user,
                        role=permission_request.target_iam_role,
                    )
            elif permission_request.request_type == 'menu' and permission_request.target_menu:
                UserDirectPermission.objects.update_or_create(
                    user=permission_request.user, menu=permission_request.target_menu,
                    defaults={'granted_by': request.user})
                # Grant only app access (not all permissions for the app)
                menu_app = permission_request.target_menu.app
                if menu_app:
                    access_perm, _ = IAMPermission.objects.get_or_create(
                        codename=f'{menu_app}:access',
                        defaults={'label': f'{menu_app} 访问', 'app': menu_app, 'scope': 'platform'},
                    )
                    UserDirectPermission.objects.update_or_create(
                        user=permission_request.user, permission=access_perm,
                        defaults={'granted_by': request.user})
                # Grant selected buttons (or all if none selected) — MenuButton deprecated
                selected = permission_request.selected_buttons or []
                from iam.models.page_config import PageButton
                if permission_request.target_menu:
                    qs = PageButton.objects.filter(tab__app=permission_request.target_menu.app)
                    for btn in qs:
                        if not selected or btn.id in selected:
                            if btn.required_perm:
                                perm = IAMPermission.objects.filter(codename=btn.required_perm).first()
                                if perm:
                                    UserDirectPermission.objects.update_or_create(
                                        user=permission_request.user, permission=perm,
                                        defaults={'granted_by': request.user})
            elif permission_request.request_type == 'permission' and permission_request.target_permission:
                from iam.models.permission import IAMPermission
                perm = IAMPermission.objects.filter(codename=permission_request.target_permission).first()
                if perm:
                    UserDirectPermission.objects.update_or_create(
                        user=permission_request.user, permission=perm,
                        defaults={'granted_by': request.user})
            elif permission_request.request_type == 'menu_button' and permission_request.target_menu_button:
                UserDirectPermission.objects.update_or_create(
                    user=permission_request.user, menu_button=permission_request.target_menu_button,
                    defaults={'granted_by': request.user})
            elif permission_request.request_type == 'project_role' and permission_request.target_project:
                from iam.models import ProjectMember
                ProjectMember.objects.update_or_create(
                    project=permission_request.target_project,
                    user=permission_request.user,
                    defaults={'role': permission_request.target_project_role or 'viewer'},
                )
                # 通知申请人
                _notify_user(permission_request.user, 'approved', permission_request)

        # 通知申请人
        _notify_user(permission_request.user, 'approved', permission_request)
        return SuccessResponse(data=PermissionRequestSerializer(permission_request).data, msg='Approved')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        permission_request = self.get_object()
        if permission_request.status != 'pending':
            return ErrorResponse(msg='Invalid status')
        # 审批权限：superuser OR 目标项目的 Business Admin
        if not request.user.is_superuser:
            if permission_request.request_type == 'project_role' and permission_request.target_project:
                from iam.resolvers import has_business_role
                if not has_business_role(request.user, permission_request.target_project.business_id, 'admin'):
                    return ErrorResponse(msg='No permission')
            else:
                return ErrorResponse(msg='No permission')

        ser = PermissionRequestReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        permission_request.status = 'rejected'
        permission_request.reviewer = request.user
        permission_request.review_comment = ser.validated_data.get('review_comment', '')
        permission_request.reviewed_at = timezone.now()
        permission_request.save()
        _notify_user(permission_request.user, 'rejected', permission_request)
        return SuccessResponse(data=PermissionRequestSerializer(permission_request).data, msg='Rejected')

    @action(detail=False, methods=['get'])
    def available_roles(self, request):
        from iam.models.permission import IAMRole
        data = IAMRole.objects.values('id', 'name')
        return SuccessResponse(data=list(data))

    @action(detail=False, methods=['get'])
    def available_menus(self, request):
        qs = IAMMenu.objects.filter(status=1, visible=1).values('id', 'name', 'parent', 'web_path')
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_permissions(request):
    """Return current user's unified IAM permissions for a given project."""
    from iam.models import IAMPermission, Project
    from iam.models.rbac import UserDirectPermission
    from iam.models.permission import IAMRolePermission

    project_id = request.query_params.get('project_id')
    if not project_id:
        return ErrorResponse(msg='project_id required')

    try:
        project_id = int(project_id)
    except (ValueError, TypeError):
        return ErrorResponse(msg='project_id must be an integer')

    user = request.user

    # ── 1. Determine IAM project role ──
    from iam.resolvers import get_project_role
    project_role = get_project_role(user, project_id) or 'viewer'

    # ── 2. Determine visible pages from IAMPermission by app ──
    # Get all apps the user has ANY permission for
    perm_apps = set()
    if user.is_superuser:
        perm_apps = set(IAMPermission.objects.values_list('app', flat=True).distinct())
    else:
        # From role-based permissions
        for rp in IAMRolePermission.objects.filter(
            role__user_roles__user=user
        ).select_related('permission').values('permission__app').distinct():
            perm_apps.add(rp['permission__app'])
        # From direct permissions
        for dp in UserDirectPermission.objects.filter(
            user=user, permission__isnull=False
        ).select_related('permission').values('permission__app').distinct():
            perm_apps.add(dp['permission__app'])

    # ── 3. Build page list from user's perm apps + project role ──
    APP_NAME_MAP = {
        'opsflow': 'OPSflow', 'itsm': 'ITSM', 'cmdb': 'CMDB',
        'system': '消息中心', 'portal': '门户', 'iam': 'IAM',
        'monitor': '监控', 'system_admin': '系统管理',
        'integration': '集成中心', 'open_api': '开放接口',
        'job_platform': '作业平台', 'agent_app': 'Agent', 'opsagent': '运维助手',
    }
    pages = []
    for app in sorted(perm_apps):
        label = APP_NAME_MAP.get(app, app)
        pages.append({'key': app, 'label_en': label, 'label_zh': label, 'visible': True})

    # ── 3. Categorize permissions by app + role level ──
    perm_keys = set()
    # Classify permission codenames into role levels
    ADMIN_KEYWORDS = {'delete', 'cancel', 'publish'}
    EDITOR_KEYWORDS = {'create', 'update', 'edit', 'run', 'manage', 'assign', 'approve', 'close'}
    VIEWER_KEYWORDS = {'search', 'retrieve', 'view', 'list', 'read', 'access'}
    if user.is_superuser:
        perm_keys = set(IAMPermission.objects.values_list('codename', flat=True))
    else:
        from iam.models.permission import IAMRolePermission, IAMUserRole
        # From IAMRolePermissions (new system)
        for rp in IAMRolePermission.objects.filter(
            role__user_roles__user=user
        ).select_related('permission'):
            perm_keys.add(rp.permission.codename)
        # From UserDirectPermission (new field)
        for dp in UserDirectPermission.objects.filter(
            user=user, permission__isnull=False
        ).select_related('permission'):
            perm_keys.add(dp.permission.codename)

    # Group by app and role level
    from collections import defaultdict
    grouped = defaultdict(list)
    for k in sorted(perm_keys):
        app = k.split(':')[0] if ':' in k else 'other'
        grouped[app].append(k)

    # Build per-app role mapping
    def classify_role(permissions: list[str]) -> str:
        """Classify a set of permissions into admin/editor/viewer"""
        perm_names = [p.split(':')[-1] for p in permissions]
        if any(kw in ' '.join(perm_names) for kw in ['delete', 'cancel', 'publish']):
            return 'admin'
        if any(kw in ' '.join(perm_names) for kw in ['create', 'update', 'edit', 'run', 'manage', 'assign']):
            return 'editor'
        return 'viewer'

    app_roles = {}
    for app, perms in sorted(grouped.items()):
        app_roles[app.lower()] = {
            'app': app.upper(),
            'role': classify_role(perms),
            'permissions': perms,
        }

    return DetailResponse(data={
        'role': project_role,
        'project_id': project_id,
        'pages': pages,
        'permissions': sorted(perm_keys),
        'permission_groups': [
            {'app': app.upper(), 'keys': keys}
            for app, keys in sorted(grouped.items())
        ],
        'app_roles': app_roles,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_full_permissions(request):
    """返回当前用户的全部权限 codename 列表（含平台级和项目级）"""

    user = request.user
    if user.is_superuser:
        from iam.models import IAMPermission
        perms = list(IAMPermission.objects.values_list('codename', flat=True))
    else:
        perms = set()
        # Collect via direct UserDirectPermission
        from iam.models.rbac import UserDirectPermission
        for dp in UserDirectPermission.objects.filter(
            user=user, permission__isnull=False
        ).select_related('permission'):
            perms.add(dp.permission.codename)
        # Collect via role-based permissions
        from iam.models.permission import IAMRolePermission
        for rp in IAMRolePermission.objects.filter(
            role__user_roles__user=user,
        ).select_related('permission'):
            perms.add(rp.permission.codename)
    return SuccessResponse(data=sorted(perms))


# ═══════════════════════════════════════════════════════════════════════════
# Page Permissions — 根据 PageTab/PageButton 配置返回用户可见的 tab + button
# ═══════════════════════════════════════════════════════════════════════════


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def page_permissions(request):
    """Return visible tabs and buttons for a given app based on user permissions."""
    app = request.query_params.get('app')
    if not app:
        return ErrorResponse(msg='app required')

    user = request.user
    from iam.models.permission import IAMRolePermission
    from iam.models.rbac import UserDirectPermission
    from iam.models.page_config import PageTab

    user_perms = set()
    if user.is_superuser:
        from iam.models import IAMPermission
        user_perms = set(IAMPermission.objects.filter(app=app).values_list('codename', flat=True))
    else:
        for rp in IAMRolePermission.objects.filter(
            role__user_roles__user=user, permission__app=app
        ).select_related('permission'):
            user_perms.add(rp.permission.codename)
        for dp in UserDirectPermission.objects.filter(
            user=user, permission__app=app
        ).select_related('permission'):
            if dp.permission:
                user_perms.add(dp.permission.codename)

    tabs_data = []
    for tab in PageTab.objects.filter(app=app, visible=True).order_by('sort'):
        tab_has_access = not tab.required_perm or tab.required_perm in user_perms
        buttons_data = []
        for btn in tab.buttons.order_by('sort'):
            buttons_data.append({
                'key': btn.key, 'label_zh': btn.label_zh, 'label_en': btn.label_en,
                'icon': btn.icon, 'required_perm': btn.required_perm,
                'has_access': btn.required_perm in user_perms,
                'style': btn.style,
            })
        tabs_data.append({
            'key': tab.key, 'label_zh': tab.label_zh, 'label_en': tab.label_en,
            'icon': tab.icon, 'is_default': tab.is_default,
            'required_perm': tab.required_perm, 'has_access': tab_has_access,
            'buttons': buttons_data,
        })

    return SuccessResponse(data={
        'app': app,
        'user_permissions': sorted(user_perms),
        'tabs': tabs_data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permission_catalog(request):
    """返回所有子产品的权限目录 — 按 app → tab → button 组织，用于权限申请页面"""
    from iam.models.page_config import PageTab, PageButton

    catalog = []
    for app_name in ['opsflow', 'itsm', 'cmdb']:
        tabs = []
        for tab in PageTab.objects.filter(app=app_name, visible=True).order_by('sort'):
            buttons = []
            for btn in PageButton.objects.filter(tab=tab).order_by('sort'):
                buttons.append({
                    'key': btn.key,
                    'label_zh': btn.label_zh,
                    'label_en': btn.label_en,
                    'required_perm': btn.required_perm,
                })
            tabs.append({
                'key': tab.key,
                'label_zh': tab.label_zh,
                'label_en': tab.label_en,
                'icon': tab.icon,
                'required_perm_tab': tab.required_perm,
                'buttons': buttons,
            })
        catalog.append({
            'app': app_name,
            'tabs': tabs,
        })

    return SuccessResponse(data=catalog)
