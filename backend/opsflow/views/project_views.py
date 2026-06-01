"""OpsProject ViewSet — 项目 CRUD + 成员管理 + 我的项目"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import OpsProject, ProjectMember
from dvadmin.utils.json_response import DetailResponse, SuccessResponse


class OpsProjectViewSet(viewsets.ModelViewSet):
    """项目管理 CRUD + 成员管理"""
    queryset = OpsProject.objects.all()
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'description']
    ordering = ['name']

    def get_queryset(self):
        """只返回当前用户有权限的项目"""
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        user_project_ids = ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True)
        return qs.filter(id__in=user_project_ids)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = [
            {
                'id': p.id, 'name': p.name, 'description': p.description,
                'is_active': p.is_active,
                'owner_name': p.owner.username if p.owner else None,
                'template_count': p.templates.count(),
                'execution_count': p.executions.count(),
                'created_at': p.created_at.isoformat(),
            }
            for p in queryset
        ]
        return SuccessResponse(data=data)

    def retrieve(self, request, *args, **kwargs):
        p = self.get_object()
        data = {
            'id': p.id, 'name': p.name, 'description': p.description,
            'is_active': p.is_active,
            'owner_name': p.owner.username if p.owner else None,
            'created_at': p.created_at.isoformat(),
        }
        return DetailResponse(data=data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(owner=request.user)
        # 创建者自动加入为 ADMIN
        ProjectMember.objects.get_or_create(
            project=project, user=request.user,
            defaults={'role': ProjectMember.Role.ADMIN},
        )
        return DetailResponse(data=serializer.data, msg='Project created')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return DetailResponse(data=serializer.data, msg='success')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.templates.exists():
            return Response(
                {'code': 4000, 'msg': 'Project has templates, delete them first', 'data': None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.delete()
        return Response({'code': 2000, 'msg': 'success', 'data': None})

    # ── 成员管理 ──────────────────────────────────────────────────────

    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        """GET: 成员列表 | POST: 添加成员"""
        project = self.get_object()

        if request.method == 'GET':
            members = ProjectMember.objects.filter(
                project=project
            ).select_related('user')
            data = [
                {
                    'id': m.id,
                    'user_id': m.user.id,
                    'username': m.user.username,
                    'role': m.role,
                    'joined_at': m.joined_at.isoformat(),
                }
                for m in members
            ]
            return SuccessResponse(data=data)

        # POST: 添加成员
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'editor')
        if not user_id:
            return Response({'code': 4000, 'msg': 'user_id required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        _, created = ProjectMember.objects.get_or_create(
            project=project, user_id=user_id,
            defaults={'role': role},
        )
        return DetailResponse(data={'created': created}, msg='Member added')

    @action(detail=True, methods=['delete'], url_path='members/(?P<member_id>[^/.]+)')
    def remove_member(self, request, pk=None, member_id=None):
        """移除成员"""
        project = self.get_object()
        try:
            m = ProjectMember.objects.get(id=member_id, project=project)
            # 不能移除自己
            if m.user == request.user:
                return Response({'code': 4000, 'msg': 'Cannot remove yourself', 'data': None},
                                status=status.HTTP_400_BAD_REQUEST)
            m.delete()
            return Response({'code': 2000, 'msg': 'Member removed', 'data': None})
        except ProjectMember.DoesNotExist:
            return Response({'code': 4000, 'msg': 'Member not found', 'data': None},
                            status=status.HTTP_404_NOT_FOUND)

    # ── 我的项目 ────────────────────────────────────────────────────

    @action(detail=False, methods=['get'])
    def my_projects(self, request):
        """返回当前用户的所有项目列表（供前端切换器用）"""
        user = request.user
        if user.is_superuser:
            projects = OpsProject.objects.all()
        else:
            memberships = ProjectMember.objects.filter(user=user).select_related('project')
            data = [
                {'id': m.project.id, 'name': m.project.name, 'role': m.role}
                for m in memberships
            ]
            return SuccessResponse(data=data)

        data = [
            {'id': p.id, 'name': p.name, 'role': 'admin'}
            for p in projects
        ]
        return SuccessResponse(data=data)


    # ── 环境变量管理 ────────────────────────────────────────────────

    @action(detail=True, methods=['get', 'post', 'patch'], url_path='env-vars')
    def env_vars(self, request, pk=None):
        """项目级环境变量 CRUD"""
        from opsflow.models import ProjectEnvironmentVariable
        from opsflow.serializers import ProjectEnvironmentVariableSerializer
        project = self.get_object()
        if request.method == 'GET':
            qs = ProjectEnvironmentVariable.objects.filter(project=project).order_by('key')
            ser = ProjectEnvironmentVariableSerializer(qs, many=True)
            return SuccessResponse(data=ser.data)
        if request.method == 'POST':
            ProjectEnvironmentVariable.objects.filter(project=project).delete()
            items = request.data.get('items', request.data)
            if isinstance(items, dict):
                items = [{'key': k, 'value': v.get('value', v) if isinstance(v, dict) else v,
                          'var_type': v.get('var_type', 'input') if isinstance(v, dict) else 'input'}
                         for k, v in items.items()]
            created = []
            for item in items:
                ser = ProjectEnvironmentVariableSerializer(data=item)
                ser.is_valid(raise_exception=True)
                ser.save(project=project)
                created.append(ser.data)
            return SuccessResponse(data=created, msg=f'{len(created)} variable(s) saved')
        items = request.data.get('items', request.data)
        results = []
        if isinstance(items, dict):
            items = [{'key': k, 'value': v.get('value', v) if isinstance(v, dict) else v,
                      'var_type': v.get('var_type', 'input') if isinstance(v, dict) else 'input'}
                     for k, v in items.items()]
        for item in items:
            obj, _ = ProjectEnvironmentVariable.objects.update_or_create(
                project=project, key=item.get('key'),
                defaults={'value': item.get('value', ''), 'var_type': item.get('var_type', 'input'),
                          'description': item.get('description', '')},
            )
            results.append(ProjectEnvironmentVariableSerializer(obj).data)
        return SuccessResponse(data=results, msg=f'{len(results)} variable(s) updated')
