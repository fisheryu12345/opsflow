"""Execution Lifecycle — 启动/暂停/恢复/取消端点 Mixin"""

from rest_framework.decorators import action

from opsflow.core.flow_engine import FlowEngine
from opsflow.core.states import PipelineState, validate_pipeline_transition
from opsflow.core.error_codes import ErrorCodes, api_success, api_error
from opsflow.serializers import FlowExecutionSerializer


class ExecutionLifecycleMixin:
    """执行生命周期端点混入（start/pause/resume/cancel）"""

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
    def cancel(self, request, pk=None):
        """取消终止执行"""
        execution = self.get_object()
        if not validate_pipeline_transition(execution.status, PipelineState.CANCELLED):
            return api_error(ErrorCodes.INVALID_STATE,
                             msg=f"不能取消（当前: {execution.status}）")
        engine = FlowEngine(execution)
        engine.cancel()
        return api_success(data=FlowExecutionSerializer(execution).data, msg='已取消')
