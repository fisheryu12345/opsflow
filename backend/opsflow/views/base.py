"""ViewSet 基类 — 项目隔离支持

ProjectFilteredViewSet 自动按项目成员关系过滤数据，
未授权的用户无法访问其他项目的数据。
"""

from django.db.models import Q
from rest_framework import viewsets, exceptions


class ProjectFilteredViewSet(viewsets.ModelViewSet):
    """自动按项目过滤的 ViewSet 基类（需成员校验）

    - 传 ?project_id=X → 仅返回该项目资源，校验当前用户是成员
    - 不传 project_id   → 返回当前用户有权限的所有项目资源
    - perform_create 自动校验用户是目标项目成员
    """
    project_field = 'project'  # 模型上的 project FK 字段名
    include_public = False     # 设为 True 时同时返回对该项目可见的公共资源

    def get_user_project_ids(self):
        """获取当前用户有权限的项目 ID 列表"""
        from opsflow.models import ProjectMember
        user = self.request.user
        if user.is_superuser:
            from opsflow.models import OpsProject
            return list(OpsProject.objects.values_list('id', flat=True))
        return list(ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True))

    def _add_public_q(self, q=None, project_id=None, user_project_ids=None):
        """如果 include_public=True，追加公共资源的查询条件"""
        q = q or Q()
        if not self.include_public:
            return q
        if project_id is not None:
            return q | Q(is_public=True, project_scope__contains='*') | Q(is_public=True, project_scope__contains=str(project_id))
        # 未指定项目：返回全部公共资源 + 对用户任一项目可见的公共资源
        q = q | Q(is_public=True, project_scope__contains='*')
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
                raise exceptions.PermissionDenied('无权访问该项目')
            base_q = Q(**{self.project_field + '_id': project_id})
            base_q = self._add_public_q(base_q, project_id=project_id)
            return qs.filter(base_q)
        base_q = Q(**{self.project_field + '__in': user_project_ids})
        base_q = self._add_public_q(base_q, user_project_ids=user_project_ids)
        return qs.filter(base_q)

    def perform_create(self, serializer):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            user_project_ids = self.get_user_project_ids()
            if int(project_id) in user_project_ids:
                serializer.save(project_id=project_id)
                return
            raise exceptions.PermissionDenied('无权在当前项目创建资源')
        # 无 project_id 时使用默认项目
        from opsflow.models import OpsProject
        default = OpsProject.objects.first()
        if default:
            serializer.save(project=default)
        else:
            serializer.save()


class ProjectReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """只读版 ProjectFilteredViewSet"""
    project_field = 'project'
    include_public = False

    def get_user_project_ids(self):
        from opsflow.models import ProjectMember
        user = self.request.user
        if user.is_superuser:
            from opsflow.models import OpsProject
            return list(OpsProject.objects.values_list('id', flat=True))
        return list(ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True))

    def _add_public_q(self, q=None, project_id=None, user_project_ids=None):
        q = q or Q()
        if not self.include_public:
            return q
        if project_id is not None:
            return q | Q(is_public=True, project_scope__contains='*') | Q(is_public=True, project_scope__contains=str(project_id))
        q = q | Q(is_public=True, project_scope__contains='*')
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
                raise exceptions.PermissionDenied('无权访问该项目')
            base_q = Q(**{self.project_field + '_id': project_id})
            base_q = self._add_public_q(base_q, project_id=project_id)
            return qs.filter(base_q)
        base_q = Q(**{self.project_field + '__in': user_project_ids})
        base_q = self._add_public_q(base_q, user_project_ids=user_project_ids)
        return qs.filter(base_q)
