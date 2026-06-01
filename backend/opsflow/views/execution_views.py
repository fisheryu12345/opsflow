"""FlowExecution ViewSet — 执行 CRUD

标准 CRUD 操作保留在此文件中。生命周期、节点命令、审批、
轨迹查询已提取到 views/mixins/ 中的 Mixin 类。
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from opsflow.models import FlowExecution
from opsflow.serializers import FlowExecutionSerializer, FlowExecutionDetailSerializer
from opsflow.views.base import ProjectFilteredViewSet
from opsflow.views.mixins.execution_lifecycle import ExecutionLifecycleMixin
from opsflow.views.mixins.execution_node_command import ExecutionNodeCommandMixin
from opsflow.views.mixins.execution_approval import ExecutionApprovalMixin
from opsflow.views.mixins.execution_trace import ExecutionTraceMixin
from dvadmin.utils.json_response import DetailResponse, SuccessResponse


class FlowExecutionViewSet(
    ExecutionLifecycleMixin,
    ExecutionNodeCommandMixin,
    ExecutionApprovalMixin,
    ExecutionTraceMixin,
    ProjectFilteredViewSet,
):
    queryset = FlowExecution.objects.all()
    serializer_class = FlowExecutionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'template', 'project']
    ordering = ['-created_at']
    project_field = 'project'

    def get_serializer_class(self):
        """详情页使用 FlowExecutionDetailSerializer（含 state_tree + trace_summary）"""
        if self.action == 'retrieve':
            return FlowExecutionDetailSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        execution = serializer.save(created_by=self.request.user)
        # 为新执行初始化 state_tree
        if not execution.state_tree:
            execution.state_tree = {}
        # 冻结创建时的模板快照到专用字段（实现执行隔离）
        template = execution.template
        if template and template.pipeline_tree:
            snapshot_tree = template.snapshot.get('pipeline_tree') if template.snapshot else None
            if not snapshot_tree:
                snapshot_tree = template.pipeline_tree
            execution.template_snapshot = {
                'pipeline_tree': snapshot_tree,
                'target_hosts': template.target_hosts,
                'global_vars': template.global_vars,
                'template_version': template.version,
            }
            execution.save(update_fields=['state_tree', 'template_snapshot'])
            # ── 执行节点持久化 ──
            from opsflow.core.node_sync import sync_execution_nodes
            sync_execution_nodes(execution)
            # ── 结束 ──

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
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
        # ── 执行方案支持 ──
        scheme_id = request.data.get('scheme_id')
        if scheme_id and serializer.instance:
            from opsflow.models import ExecutionScheme
            try:
                scheme = ExecutionScheme.objects.get(id=scheme_id, template=serializer.instance.template)
                if scheme.excluded_nodes:
                    serializer.instance.excluded_nodes = scheme.excluded_nodes
                    serializer.instance.save(update_fields=['excluded_nodes'])
            except ExecutionScheme.DoesNotExist:
                pass
        # ── 结束 ──
        # ── 变量覆盖支持 ──
        variable_overrides = request.data.get('variable_overrides', {})
        if variable_overrides and serializer.instance and serializer.instance.template_snapshot:
            frozen_vars = dict(serializer.instance.template_snapshot.get('global_vars', {}))
            for key, value in variable_overrides.items():
                if key in frozen_vars:
                    if isinstance(frozen_vars[key], dict) and 'value' in frozen_vars[key]:
                        frozen_vars[key] = dict(frozen_vars[key])
                        frozen_vars[key]['value'] = value
                    else:
                        frozen_vars[key] = value
            serializer.instance.template_snapshot['global_vars'] = frozen_vars
            serializer.instance.save(update_fields=['template_snapshot'])
        # ── 结束 ──
        return DetailResponse(data=serializer.data, msg="创建成功")
