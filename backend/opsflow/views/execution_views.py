from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import FlowExecution, FlowTemplate
from opsflow.serializers import FlowExecutionSerializer
from opsflow.core.flow_engine import FlowEngine
from dvadmin.utils.json_response import DetailResponse, SuccessResponse


class FlowExecutionViewSet(viewsets.ModelViewSet):
    queryset = FlowExecution.objects.all()
    serializer_class = FlowExecutionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'template']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        execution = serializer.save(created_by=self.request.user)
        # 快照模板的 pipeline_tree（含固化位置）到执行实例，
        # 确保编辑视图和执行视图的流程图式样一致
        template = serializer.validated_data.get('template')
        if template and template.pipeline_tree:
            context = execution.context or {}
            context['pipeline_tree'] = template.pipeline_tree
            execution.context = context
            execution.save(update_fields=['context'])

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
        if execution.status not in ('pending', 'failed', 'paused'):
            return Response({'code': 4000, 'msg': '当前状态不允许启动', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        engine = FlowEngine(execution)
        engine.start()
        return Response({'code': 2000, 'msg': '执行已启动', 'data': FlowExecutionSerializer(execution).data})

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停执行"""
        execution = self.get_object()
        if execution.status != 'running':
            return Response({'code': 4000, 'msg': '仅运行中的任务可暂停', 'data': None})
        engine = FlowEngine(execution)
        engine.pause()
        return Response({'code': 2000, 'msg': '已暂停', 'data': FlowExecutionSerializer(execution).data})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """恢复执行"""
        execution = self.get_object()
        if execution.status != 'paused':
            return Response({'code': 4000, 'msg': '仅已暂停的任务可恢复', 'data': None})
        execution.status = FlowExecution.Status.RUNNING
        execution.save()
        engine = FlowEngine(execution)
        engine.resume()
        return Response({'code': 2000, 'msg': '已恢复', 'data': FlowExecutionSerializer(execution).data})

    @action(detail=True, methods=['post'])
    def retry_node(self, request, pk=None):
        """重试指定节点"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        if not node_id:
            return Response({'code': 4000, 'msg': 'node_id required', 'data': None})
        engine = FlowEngine(execution)
        engine.retry(node_id)
        return Response({'code': 2000, 'msg': f'正在重试节点 {node_id}', 'data': None})

    @action(detail=True, methods=['post'])
    def skip_node(self, request, pk=None):
        """跳过指定节点"""
        execution = self.get_object()
        node_id = request.data.get('node_id')
        if not node_id:
            return Response({'code': 4000, 'msg': 'node_id required', 'data': None})
        engine = FlowEngine(execution)
        engine.skip(node_id)
        return Response({'code': 2000, 'msg': f'已跳过节点 {node_id}', 'data': None})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消终止执行"""
        execution = self.get_object()
        if execution.status not in ('running', 'paused', 'pending'):
            return Response({'code': 4000, 'msg': '当前状态不允许取消', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        engine = FlowEngine(execution)
        engine.cancel()
        return Response({'code': 2000, 'msg': '已取消', 'data': FlowExecutionSerializer(execution).data})
