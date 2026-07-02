"""ExecutionScheme ViewSet — 执行方案 CRUD（嵌套于模板下）"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import FlowTemplate, ExecutionScheme
from opsflow.serializers import ExecutionSchemeSerializer
from opsflow.views.base import ProjectFilteredViewSet
from iam.permissions import TenantPermission
from common.utils.json_response import DetailResponse, SuccessResponse


class ExecutionSchemeViewSet(ProjectFilteredViewSet):
    """执行方案 CRUD — 预定义节点排除集 + 变量覆盖"""
    queryset = ExecutionScheme.objects.all()
    serializer_class = ExecutionSchemeSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    project_field = 'project'

    def get_queryset(self):
        qs = super().get_queryset()
        template_id = self.kwargs.get('template_pk')
        if template_id:
            qs = qs.filter(template_id=template_id)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, msg="获取成功")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg="获取成功")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg="创建成功")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return DetailResponse(data=serializer.data, msg="更新成功")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({'code': 2000, 'msg': 'success', 'data': None})

    def perform_create(self, serializer):
        template_id = self.kwargs.get('template_pk')
        if template_id:
            try:
                template = FlowTemplate.objects.get(id=template_id)
            except FlowTemplate.DoesNotExist:
                return Response(
                    {'code': 4000, 'msg': 'Template not found', 'data': None},
                    status=status.HTTP_404_NOT_FOUND,
                )
            # 如设为默认方案，先清除其他方案的 is_default
            if serializer.validated_data.get('is_default'):
                ExecutionScheme.objects.filter(template=template, is_default=True).update(is_default=False)
            serializer.save(template=template, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        # 如设为默认方案，先清除其他方案的 is_default
        if serializer.validated_data.get('is_default'):
            instance = self.get_object()
            ExecutionScheme.objects.filter(template=instance.template, is_default=True).exclude(
                id=instance.id
            ).update(is_default=False)
        serializer.save()

    @action(detail=True, methods=['get'])
    def preview(self, request, template_pk=None, pk=None):
        """预览执行方案 — 返回排除节点后的清理后 pipeline_tree

        参考 bk_sops PipelineTemplateWebPreviewer.preview_pipeline_tree_exclude_task_nodes
        """
        try:
            template = FlowTemplate.objects.get(id=template_pk)
            scheme = self.get_object()
        except (FlowTemplate.DoesNotExist, ExecutionScheme.DoesNotExist):
            return Response({'code': 4000, 'msg': 'Not found', 'data': None},
                            status=status.HTTP_404_NOT_FOUND)

        pipeline_tree = template.pipeline_tree or {}
        exclude_ids = scheme.excluded_nodes or []

        from opsflow.core.pipeline_preview import PipelinePreviewService
        cleaned = PipelinePreviewService.preview_exclude_nodes(pipeline_tree, exclude_ids)

        return Response({
            'code': 2000, 'msg': 'success',
            'data': {
                'pipeline_tree': cleaned,
                'scheme': ExecutionSchemeSerializer(scheme).data,
            },
        })
