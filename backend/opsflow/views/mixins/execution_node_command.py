"""Execution Node Commands — 节点操作/批量/子流程重试端点 Mixin"""

from rest_framework.decorators import action

from opsflow.core.node_dispatcher import NodeCommandDispatcher
from opsflow.core.flow_engine import FlowEngine
from opsflow.core.error_codes import ErrorCodes, api_success, api_error


class ExecutionNodeCommandMixin:
    """节点操作端点混入（retry/skip/force_fail/batch/subprocess）"""

    def _single_node_command(self, execution, node_id, command_name, operator, **kwargs):
        """执行单节点操作并返回响应（retry/skip/force_fail 共享）"""
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        dispatcher = NodeCommandDispatcher(execution)
        method = getattr(dispatcher, command_name)
        result = method(node_id, operator=operator, **kwargs)
        if not result['result']:
            return api_error(ErrorCodes.NODE_COMMAND_FAILED, msg=result['message'])
        return api_success(msg=result['message'], data=result['data'])

    def _batch_node_command(self, execution, node_ids, command_name, operator, error_msg, success_msg_fmt):
        """批量执行节点操作（batch_retry/batch_skip 共享）"""
        failed_nodes = [
            nid for nid, st in (execution.node_status or {}).items()
            if st == 'failed' and (not node_ids or nid in node_ids)
        ]
        if not failed_nodes:
            return api_error(ErrorCodes.NODE_ID_REQUIRED, msg=error_msg)
        dispatcher = NodeCommandDispatcher(execution)
        method = getattr(dispatcher, command_name)
        results = [method(nid, operator=operator) for nid in failed_nodes]
        succeeded = sum(1 for r in results if r['result'])
        return api_success(data={
            'total': len(failed_nodes),
            'succeeded': succeeded,
            'failed': len(failed_nodes) - succeeded,
            'results': results,
        }, msg=success_msg_fmt.format(succeeded, len(failed_nodes)))

    @action(detail=True, methods=['post'])
    def retry_node(self, request, pk=None):
        """重试指定节点（通过 NodeCommandDispatcher 自动记录 Trace）"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        return self._single_node_command(execution, node_id, 'retry', operator=str(request.user))

    @action(detail=True, methods=['post'])
    def skip_node(self, request, pk=None):
        """跳过指定节点（通过 NodeCommandDispatcher 自动记录）"""
        execution = self.get_object()
        node_id = request.data.get('node_id')
        return self._single_node_command(execution, node_id, 'skip', operator=str(request.user))

    @action(detail=True, methods=['post'])
    def force_fail(self, request, pk=None):
        """强制标记指定节点为失败状态"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        reason = request.data.get('reason', '')
        return self._single_node_command(execution, node_id, 'force_fail',
                                         operator=str(request.user), reason=reason)

    # -- Batch operations ---------------------------------------------------

    @action(detail=True, methods=['post'])
    def batch_retry(self, request, pk=None):
        """批量重试所有失败节点"""
        execution = self.get_object()
        node_ids = request.data.get('node_ids')
        return self._batch_node_command(execution, node_ids, 'retry', str(request.user),
                                        error_msg='没有可重试的失败节点',
                                        success_msg_fmt='批量重试完成: {}/{} 成功')

    @action(detail=True, methods=['post'])
    def batch_skip(self, request, pk=None):
        """批量跳过所有失败节点"""
        execution = self.get_object()
        node_ids = request.data.get('node_ids')
        return self._batch_node_command(execution, node_ids, 'skip', str(request.user),
                                        error_msg='没有可跳过的失败节点',
                                        success_msg_fmt='批量跳过完成: {}/{} 成功')

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
