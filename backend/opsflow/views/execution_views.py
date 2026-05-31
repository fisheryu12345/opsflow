from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import FlowExecution, FlowTemplate, NodeExecutionTrace
from opsflow.serializers import FlowExecutionSerializer, FlowExecutionDetailSerializer, NodeExecutionTraceSerializer
from opsflow.core.flow_engine import FlowEngine
from opsflow.core.node_dispatcher import NodeCommandDispatcher
from opsflow.core.states import PipelineState, validate_pipeline_transition
from dvadmin.utils.json_response import DetailResponse, SuccessResponse


# ── 错误码 ─────────────────────────────────────────────────
_INVALID_STATE = lambda s: {'code': 4000, 'msg': f'当前状态不允许操作（当前: {s}）', 'data': None}


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
            execution.save(update_fields=['template_snapshot'])

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
            return Response(_INVALID_STATE(execution.status), status=status.HTTP_400_BAD_REQUEST)
        engine = FlowEngine(execution)
        engine.start()
        return Response({'code': 2000, 'msg': '执行已启动', 'data': FlowExecutionSerializer(execution).data})

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停执行"""
        execution = self.get_object()
        if not validate_pipeline_transition(execution.status, PipelineState.PAUSED):
            return Response(_INVALID_STATE(execution.status))
        engine = FlowEngine(execution)
        engine.pause()
        return Response({'code': 2000, 'msg': '已暂停', 'data': FlowExecutionSerializer(execution).data})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """恢复执行"""
        execution = self.get_object()
        if not validate_pipeline_transition(execution.status, PipelineState.RUNNING):
            return Response(_INVALID_STATE(execution.status))
        execution.status = PipelineState.RUNNING
        execution.save()
        engine = FlowEngine(execution)
        engine.resume()
        return Response({'code': 2000, 'msg': '已恢复', 'data': FlowExecutionSerializer(execution).data})

    @action(detail=True, methods=['post'])
    def retry_node(self, request, pk=None):
        """重试指定节点（通过 NodeCommandDispatcher 自动记录 Trace）"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        if not node_id:
            return Response({'code': 4000, 'msg': 'node_id required', 'data': None})
        dispatcher = NodeCommandDispatcher(execution)
        result = dispatcher.retry(node_id, operator=str(request.user))
        if not result['result']:
            return Response({'code': 4000, 'msg': result['message'], 'data': None})
        return Response({'code': 2000, 'msg': result['message'], 'data': result['data']})

    @action(detail=True, methods=['post'])
    def skip_node(self, request, pk=None):
        """跳过指定节点（通过 NodeCommandDispatcher 自动记录）"""
        execution = self.get_object()
        node_id = request.data.get('node_id')
        if not node_id:
            return Response({'code': 4000, 'msg': 'node_id required', 'data': None})
        dispatcher = NodeCommandDispatcher(execution)
        result = dispatcher.skip(node_id, operator=str(request.user))
        if not result['result']:
            return Response({'code': 4000, 'msg': result['message'], 'data': None})
        return Response({'code': 2000, 'msg': result['message'], 'data': result['data']})

    # -- Trace endpoints ----------------------------------------------------

    @action(detail=True, methods=['get'])
    def traces(self, request, pk=None):
        """获取节点轨迹列表，支持 ?node_id=xxx 过滤单个节点"""
        execution = self.get_object()
        node_id = request.query_params.get('node_id')
        if node_id:
            dispatcher = NodeCommandDispatcher(execution)
            result = dispatcher.get_trace(node_id)
            return Response({
                'code': 2000, 'msg': 'success',
                'data': {'state_tree': execution.state_tree or {}, 'traces': result['data']},
            })
        # 全部轨迹摘要
        qs = NodeExecutionTrace.objects.filter(execution=execution).order_by('entered_at')
        serializer = NodeExecutionTraceSerializer(qs, many=True)
        return Response({
            'code': 2000, 'msg': 'success',
            'data': {
                'state_tree': execution.state_tree or {},
                'traces': serializer.data,
            },
        })

    @action(detail=True, methods=['get'])
    def trace_log(self, request, pk=None):
        """读取节点日志文件内容"""
        node_id = request.query_params.get('node_id')
        if not node_id:
            return Response({'code': 4000, 'msg': 'node_id required'})
        dispatcher = NodeCommandDispatcher(self.get_object())
        result = dispatcher.get_trace_log(node_id)
        if not result['result']:
            return Response({'code': 4000, 'msg': result['message'], 'data': None})
        return Response({'code': 2000, 'msg': 'success', 'data': result['data']})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消终止执行"""
        execution = self.get_object()
        if not validate_pipeline_transition(execution.status, PipelineState.CANCELLED):
            return Response(_INVALID_STATE(execution.status), status=status.HTTP_400_BAD_REQUEST)
        engine = FlowEngine(execution)
        engine.cancel()
        return Response({'code': 2000, 'msg': '已取消', 'data': FlowExecutionSerializer(execution).data})
