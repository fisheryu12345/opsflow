from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import FlowExecution, FlowTemplate, NodeExecutionTrace
from opsflow.serializers import FlowExecutionSerializer, FlowExecutionDetailSerializer, NodeExecutionTraceSerializer
from opsflow.core.flow_engine import FlowEngine
from opsflow.core.node_dispatcher import NodeCommandDispatcher
from opsflow.core.states import PipelineState, validate_pipeline_transition
from opsflow.core.error_codes import ErrorCodes, api_success, api_error
from dvadmin.utils.json_response import DetailResponse, SuccessResponse


class FlowExecutionViewSet(viewsets.ModelViewSet):
    queryset = FlowExecution.objects.all()
    serializer_class = FlowExecutionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'template']
    ordering = ['-created_at']

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
        return DetailResponse(data=serializer.data, msg="创建成功")

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动执行 — 触发 Celery 异步任务"""
        execution = self.get_object()
        if not validate_pipeline_transition(execution.status, PipelineState.RUNNING):
            return api_error(ErrorCodes.INVALID_STATE,
                             msg=f"不能启动（当前: {execution.status}）")
        engine = FlowEngine(execution)
        engine.start()
        return api_success(data=FlowExecutionSerializer(execution).data, msg='执行已启动')

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停执行"""
        execution = self.get_object()
        if not validate_pipeline_transition(execution.status, PipelineState.PAUSED):
            return api_error(ErrorCodes.INVALID_STATE,
                             msg=f"不能暂停（当前: {execution.status}）")
        engine = FlowEngine(execution)
        engine.pause()
        return api_success(data=FlowExecutionSerializer(execution).data, msg='已暂停')

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """恢复执行"""
        execution = self.get_object()
        if not validate_pipeline_transition(execution.status, PipelineState.RUNNING):
            return api_error(ErrorCodes.INVALID_STATE,
                             msg=f"不能恢复（当前: {execution.status}）")
        execution.status = PipelineState.RUNNING
        execution.save()
        engine = FlowEngine(execution)
        engine.resume()
        return api_success(data=FlowExecutionSerializer(execution).data, msg='已恢复')

    @action(detail=True, methods=['post'])
    def retry_node(self, request, pk=None):
        """重试指定节点（通过 NodeCommandDispatcher 自动记录 Trace）"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        dispatcher = NodeCommandDispatcher(execution)
        result = dispatcher.retry(node_id, operator=str(request.user))
        if not result['result']:
            return api_error(ErrorCodes.NODE_COMMAND_FAILED, msg=result['message'])
        return api_success(msg=result['message'], data=result['data'])

    @action(detail=True, methods=['post'])
    def skip_node(self, request, pk=None):
        """跳过指定节点（通过 NodeCommandDispatcher 自动记录）"""
        execution = self.get_object()
        node_id = request.data.get('node_id')
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        dispatcher = NodeCommandDispatcher(execution)
        result = dispatcher.skip(node_id, operator=str(request.user))
        if not result['result']:
            return api_error(ErrorCodes.NODE_COMMAND_FAILED, msg=result['message'])
        return api_success(msg=result['message'], data=result['data'])

    @action(detail=True, methods=['post'])
    def force_fail(self, request, pk=None):
        """强制标记指定节点为失败状态"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        reason = request.data.get('reason', '')
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        dispatcher = NodeCommandDispatcher(execution)
        result = dispatcher.force_fail(node_id, operator=str(request.user), reason=reason)
        if not result['result']:
            return api_error(ErrorCodes.NODE_COMMAND_FAILED, msg=result['message'])
        return api_success(msg=result['message'], data=result['data'])

    # -- Trace endpoints ----------------------------------------------------

    @action(detail=True, methods=['get'])
    def traces(self, request, pk=None):
        """获取节点轨迹列表，支持 ?node_id=xxx 过滤单个节点"""
        execution = self.get_object()
        node_id = request.query_params.get('node_id')
        if node_id:
            dispatcher = NodeCommandDispatcher(execution)
            result = dispatcher.get_trace(node_id)
            return api_success(data={
                'state_tree': execution.state_tree or {},
                'traces': result['data'],
            })
        qs = NodeExecutionTrace.objects.filter(execution=execution).order_by('entered_at')
        serializer = NodeExecutionTraceSerializer(qs, many=True)
        return api_success(data={
            'state_tree': execution.state_tree or {},
            'traces': serializer.data,
        })

    @action(detail=True, methods=['get'])
    def trace_log(self, request, pk=None):
        """读取节点日志文件内容"""
        node_id = request.query_params.get('node_id')
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        dispatcher = NodeCommandDispatcher(self.get_object())
        result = dispatcher.get_trace_log(node_id)
        if not result['result']:
            return api_error(ErrorCodes.NODE_COMMAND_FAILED, msg=result['message'])
        return api_success(data=result['data'])

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消终止执行"""
        execution = self.get_object()
        if not validate_pipeline_transition(execution.status, PipelineState.CANCELLED):
            return api_error(ErrorCodes.INVALID_STATE,
                             msg=f"不能取消（当前: {execution.status}）")
        engine = FlowEngine(execution)
        engine.cancel()
        return api_success(data=FlowExecutionSerializer(execution).data, msg='已取消')
