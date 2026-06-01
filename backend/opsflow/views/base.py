"""ViewSet 基类 — 项目隔离支持

ProjectFilteredViewSet 自动按 project_id 过滤数据，
所有 OpsFlow ViewSet 应继承此类。
"""

from rest_framework import viewsets


class ProjectFilteredViewSet(viewsets.ModelViewSet):
    """自动按项目过滤的 ViewSet 基类

    要求请求参数中包含 project_id。如果不提供 project_id，
    行为取决于 allow_no_project 属性：
      - False（默认）: 返回空 queryset（必须选项目）
      - True: 返回所有数据（向后兼容）
    """
    allow_no_project = False
    project_field = 'project'  # 模型上的 project FK 字段名

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            filter_kwargs = {self.project_field + '_id': project_id}
            return qs.filter(**filter_kwargs)
        if self.allow_no_project:
            return qs
        return qs.none()

    def perform_create(self, serializer):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            from opsflow.models import OpsProject
            try:
                project = OpsProject.objects.get(id=project_id)
                serializer.save(project=project)
                return
            except OpsProject.DoesNotExist:
                pass
        serializer.save()


class ProjectReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """只读版 ProjectFilteredViewSet"""
    allow_no_project = False
    project_field = 'project'

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            filter_kwargs = {self.project_field + '_id': project_id}
            return qs.filter(**filter_kwargs)
        if self.allow_no_project:
            return qs
        return qs.none()
