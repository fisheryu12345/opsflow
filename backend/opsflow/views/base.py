"""ViewSet 基类 — 项目隔离支持

ProjectFilteredViewSet 自动按 project_id 过滤数据，
所有 OpsFlow ViewSet 应继承此类。
"""

from rest_framework import viewsets


class ProjectFilteredViewSet(viewsets.ModelViewSet):
    """自动按项目过滤的 ViewSet 基类

    - 传 ?project_id=X → 仅返回该项目的资源
    - 不传 project_id   → 返回全部资源（向后兼容）
    - perform_create 自动设置 project 字段
    """
    allow_no_project = True
    project_field = 'project'  # 模型上的 project FK 字段名

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            filter_kwargs = {self.project_field + '_id': project_id}
            return qs.filter(**filter_kwargs)
        return qs

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
        # 未指定 project_id 时自动分配到默认项目
        from opsflow.models import OpsProject
        default = OpsProject.objects.first()
        if default:
            serializer.save(project=default)
        else:
            serializer.save()


class ProjectReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """只读版 ProjectFilteredViewSet"""
    allow_no_project = True
    project_field = 'project'

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            filter_kwargs = {self.project_field + '_id': project_id}
            return qs.filter(**filter_kwargs)
        return qs
