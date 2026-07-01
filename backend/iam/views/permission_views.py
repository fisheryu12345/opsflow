"""IAM permission views — PermissionRequest, DirectPermission, Business, Project, etc."""
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
        elif req.request_type == 'role' and req.target_role:
            detail = f"角色 [{req.target_role.name}]"
        elif req.request_type == 'menu' and req.target_menu:
            detail = f"菜单 [{req.target_menu.name}]"
        elif req.request_type == 'menu_button' and req.target_menu_button:
            detail = f"按钮 [{req.target_menu_button.name}]"
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

            if permission_request.request_type == 'role' and permission_request.target_role:
                permission_request.user.role.add(permission_request.target_role)
            elif permission_request.request_type == 'menu' and permission_request.target_menu:
                UserDirectPermission.objects.update_or_create(
                    user=permission_request.user, menu=permission_request.target_menu,
                    defaults={'granted_by': request.user})
                # Grant selected buttons (or all if none selected)
                from iam.models.menu_rbac import MenuButton
                selected = permission_request.selected_buttons or []
                qs = MenuButton.objects.filter(menu=permission_request.target_menu)
                if selected:
                    qs = qs.filter(id__in=selected)
                for btn in qs:
                    UserDirectPermission.objects.update_or_create(
                        user=permission_request.user, menu_button=btn,
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

ALL_PAGE_DEFS = [
    # ITSM
    ('itsm-tickets', 'ITSM Tickets', 'ITSM 工单'),
    ('itsm-workflows', 'ITSM Workflows', 'ITSM 流程'),
    ('itsm-incidents', 'ITSM Incidents', 'ITSM 事件'),
    ('itsm-changes', 'ITSM Changes', 'ITSM 变更'),
    ('itsm-sla', 'ITSM SLA', 'ITSM SLA'),
    ('itsm-delegation', 'ITSM Delegation', 'ITSM 委托'),
    ('itsm-skill-groups', 'ITSM Skill Groups', 'ITSM 技能组'),
    ('itsm-on-duty', 'ITSM On-Duty', 'ITSM 排班'),
    ('itsm-assign-rules', 'ITSM Assign Rules', 'ITSM 路由'),
    ('itsm-escalation', 'ITSM Escalation', 'ITSM 升级'),
    # OPSflow
    ('opsflow-templates', 'OPSflow Templates', 'OPSflow 模板'),
    ('opsflow-executions', 'OPSflow Executions', 'OPSflow 执行'),
    ('opsflow-schedules', 'OPSflow Schedules', 'OPSflow 调度'),
    ('opsflow-webhooks', 'OPSflow Webhooks', 'OPSflow Webhook'),
    # CMDB
    ('cmdb-models', 'CMDB Models', 'CMDB 模型'),
    ('cmdb-instances', 'CMDB Instances', 'CMDB 实例'),
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
            if project.business_id: # pyright: ignore[reportAttributeAccessIssue]
                bm = BusinessMember.objects.filter(
                    business_id=project.business_id, user=user # pyright: ignore[reportAttributeAccessIssue]
                ).first()
                if bm:
                    role = bm.role
    except Project.DoesNotExist:
        return ErrorResponse(msg='Project not found', status=404)

    # Determine visible pages (all visible to editor+, some admin-only)
    is_admin = role == 'admin'
    is_editor = role == 'editor'
    pages = []
    admin_only = {'itsm-assign-rules', 'itsm-escalation', 'cmdb-models'}
    for key, label_en, label_zh in ALL_PAGE_DEFS:
        visible = True
        if key in admin_only:
            visible = is_admin
        pages.append({'key': key, 'label_en': label_en, 'label_zh': label_zh, 'visible': visible})

    # Collect all permission keys
    perm_keys = set()
    if user.is_superuser:
        from iam.models.menu_rbac import MenuButton
        perm_keys = set(MenuButton.objects.values_list('value', flat=True))
    else:
        for r in user.role.filter(status=1):
            for mbp in r.role_menu_button.select_related('menu_button').all():
                if mbp.menu_button:
                    perm_keys.add(mbp.menu_button.value)
        for dp in UserDirectPermission.objects.filter(user=user).select_related('menu_button'):
            if dp.menu_button:
                perm_keys.add(dp.menu_button.value)

    # Group permissions by app prefix
    from collections import defaultdict
    grouped = defaultdict(list)
    for k in sorted(perm_keys):
        app = k.split(':')[0] if ':' in k else 'other'
        grouped[app].append(k)

    return DetailResponse(data={
        'role': role,
        'project_id': project_id,
        'pages': pages,
        'permissions': sorted(perm_keys),
        'permission_groups': [
            {'app': app.upper(), 'keys': keys}
            for app, keys in sorted(grouped.items())
        ],
    })
