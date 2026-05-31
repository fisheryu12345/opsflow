"""FlowTemplate ViewSet — 流程模板 CRUD

标准 CRUD 操作保留在此文件中。AI 生成、版本管理、变量管理、
子流程追踪等功能已提取到 views/mixins/ 中的 Mixin 类。
"""

import logging
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from opsflow.models import FlowTemplate
from opsflow.serializers import FlowTemplateSerializer
from opsflow.views.mixins.template_ai import TemplateAIMixin
from opsflow.views.mixins.template_version import TemplateVersionMixin
from opsflow.views.mixins.template_variable import TemplateVariableMixin
from opsflow.views.mixins.template_subprocess import TemplateSubprocessMixin
from opsflow.views.mixins.template_export import TemplateExportImportMixin
from opsflow.views.mixins.template_collect import TemplateCollectMixin
from opsflow.core.audit_logger import log_operation
from dvadmin.utils.json_response import DetailResponse, SuccessResponse

logger = logging.getLogger(__name__)


class FlowTemplateViewSet(
    TemplateAIMixin,
    TemplateVersionMixin,
    TemplateVariableMixin,
    TemplateSubprocessMixin,
    TemplateExportImportMixin,
    TemplateCollectMixin,
    viewsets.ModelViewSet,
):
    queryset = FlowTemplate.objects.all()
    serializer_class = FlowTemplateSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_draft', 'created_by', 'category']
    search_fields = ['name']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_operation(self.request.user, 'create', 'template', instance.id, instance.name, request=self.request)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return SuccessResponse(data=serializer.data, page=int(request.query_params.get('page', 1)),
                                   limit=self.paginator.get_page_size(request) if hasattr(self.paginator, 'get_page_size') else 10,
                                   total=self.paginator.page.paginator.count if hasattr(self.paginator, 'page') else queryset.count())
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, total=queryset.count())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg='success')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(instance.pipeline_tree or {}, instance.global_vars or {})
        instance.global_vars = cleaned
        instance.save(update_fields=['global_vars'])
        # ── 结束 ──
        # ── 节点持久化同步（pipeline_tree 变更时） ──
        if 'pipeline_tree' in request.data:
            from opsflow.core.node_sync import sync_template_nodes
            sync_template_nodes(instance)
        # ── 结束 ──
        log_operation(self.request.user, 'update', 'template', instance.id, instance.name, request=self.request)
        return DetailResponse(data=serializer.data, msg='success')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.created_by and instance.created_by != request.user:
            return Response({'code': 4000, 'msg': 'Only the creator can delete this template', 'data': None},
                            status=status.HTTP_403_FORBIDDEN)
        log_operation(request.user, 'delete', 'template', instance.id, instance.name, request=request)
        instance.delete()
        return Response({'code': 2000, 'msg': 'success', 'data': None})
