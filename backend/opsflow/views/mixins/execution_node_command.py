"""Execution Node Commands — 节点操作/批量/子流程重试端点 Mixin"""

from rest_framework.decorators import action

from opsflow.core.node_dispatcher import NodeCommandDispatcher
from opsflow.core.flow_engine import FlowEngine
from opsflow.core.error_codes import ErrorCodes, api_success, api_error


class ExecutionNodeCommandMixin:
    """节点操作端点混入（retry/skip/force_fail/batch/subprocess）"""

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

    # -- Batch operations ---------------------------------------------------

    @action(detail=True, methods=['post'])
    def batch_retry(self, request, pk=None):
        """批量重试所有失败节点"""
        execution = self.get_object()
        node_ids = request.data.get('node_ids')
        failed_nodes = [
            nid for nid, st in (execution.node_status or {}).items()
            if st == 'failed' and (not node_ids or nid in node_ids)
        ]
        if not failed_nodes:
            return api_error(ErrorCodes.NODE_ID_REQUIRED, msg='没有可重试的失败节点')
        dispatcher = NodeCommandDispatcher(execution)
        results = []
        for nid in failed_nodes:
            results.append(dispatcher.retry(nid, operator=str(request.user)))
        succeeded = sum(1 for r in results if r['result'])
        return api_success(data={
            'total': len(failed_nodes),
            'succeeded': succeeded,
            'failed': len(failed_nodes) - succeeded,
            'results': results,
        }, msg=f'批量重试完成: {succeeded}/{len(failed_nodes)} 成功')

    @action(detail=True, methods=['post'])
    def batch_skip(self, request, pk=None):
        """批量跳过所有失败节点"""
        execution = self.get_object()
        node_ids = request.data.get('node_ids')
        failed_nodes = [
            nid for nid, st in (execution.node_status or {}).items()
            if st == 'failed' and (not node_ids or nid in node_ids)
        ]
        if not failed_nodes:
            return api_error(ErrorCodes.NODE_ID_REQUIRED, msg='没有可跳过的失败节点')
        dispatcher = NodeCommandDispatcher(execution)
        results = []
        for nid in failed_nodes:
            results.append(dispatcher.skip(nid, operator=str(request.user)))
        succeeded = sum(1 for r in results if r['result'])
        return api_success(data={
            'total': len(failed_nodes),
            'succeeded': succeeded,
            'failed': len(failed_nodes) - succeeded,
            'results': results,
        }, msg=f'批量跳过完成: {succeeded}/{len(failed_nodes)} 成功')

    # -- Subprocess operations ------------------------------------------------

    @action(detail=True, methods=['post'])
    def retry_subprocess(self, request, pk=None):
        """重试子流程节点 — 委托给 FlowEngine.retry_subprocess"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        engine = FlowEngine(execution)
        engine.retry_subprocess(node_id)
        return api_success(msg=f'正在重试子流程节点 {node_id}')
