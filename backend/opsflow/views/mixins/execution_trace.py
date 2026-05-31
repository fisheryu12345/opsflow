"""Execution Trace — 节点轨迹查询端点 Mixin"""

from rest_framework.decorators import action

from opsflow.models import NodeExecutionTrace
from opsflow.serializers import NodeExecutionTraceSerializer
from opsflow.core.node_dispatcher import NodeCommandDispatcher
from opsflow.core.error_codes import ErrorCodes, api_success, api_error


class ExecutionTraceMixin:
    """节点轨迹查询端点混入（traces/trace_log）"""

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
