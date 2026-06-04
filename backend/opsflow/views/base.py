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
                raise exceptions.PermissionDenied('No access to this project')
            base_q = Q(**{self.project_field + '_id': project_id})
            base_q = self._add_public_q(base_q, project_id=project_id)
            return qs.filter(base_q)
        base_q = Q(**{self.project_field + '__in': user_project_ids})
        base_q = self._add_public_q(base_q, user_project_ids=user_project_ids)
        return qs.filter(base_q)

    @staticmethod
    def resolve_project_kwargs(request, project_id=None):
        """解析项目归属，返回 {project} 或 {} 用于 create 调用

        统一 ViewSet/Mixin 中重复的项目归属逻辑：
        - 传 project_id → 返回 {'project_id': project_id}
        - 不传           → 返回 {'project': 默认项目}
        - 用户无权限     → 返回 {}（调用方自行决定是否报错）
        """
        pid = project_id or request.query_params.get('project_id')
        if pid:
            return {'project_id': int(pid)}
        from opsflow.models import OpsProject
        first = OpsProject.objects.first()
        return {'project': first} if first else {}

    def perform_create(self, serializer):
        kwargs = self.resolve_project_kwargs(self.request)
        if 'project_id' in kwargs:
            user_project_ids = self.get_user_project_ids()
            if kwargs['project_id'] not in user_project_ids:
                raise exceptions.PermissionDenied('No permission to create resources in this project')
        serializer.save(**kwargs)


class ProjectReadOnlyViewSet(ProjectFilteredViewSet):
    """只读版 ProjectFilteredViewSet — 禁用写操作"""
    def create(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)
    def update(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)
    def partial_update(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)
    def destroy(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)
