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

    @action(detail=False, methods=['get'])
    def pending_approval(self, request):
        """返回所有待审批的执行列表"""
        qs = self.get_queryset().filter(
            status=PipelineState.PAUSED,
        ).select_related('template', 'created_by').order_by('-created_at')
        result = []
        for ex in qs:
            ctx = ex.context or {}
            decisions = ctx.get('_approval_decisions', {})
            cn = ex.current_node
            if cn and cn not in decisions:
                result.append({
                    'id': ex.id,
                    'template_name': ex.template.name if ex.template else '',
                    'node_id': cn,
                    'status': ex.status,
                    'paused_at': ex.updated_at.isoformat() if getattr(ex, 'updated_at', None) else None,
                    'created_at': ex.created_at.isoformat() if ex.created_at else None,
                    'created_by': str(ex.created_by) if ex.created_by else '',
                })
        return api_success(data=result, msg="获取成功")

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

    # -- Approval endpoints ------------------------------------------------

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """审批通过 — 标记节点为已审批并恢复执行"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        comment = request.data.get('comment', '')
        # 记录审批信息到 context
        ctx = dict(execution.context or {})
        approval = dict(ctx.get('_approval_decisions', {}))
        approval[node_id] = {'approved': True, 'by': str(request.user),
                             'at': datetime.datetime.now().isoformat(), 'comment': comment}
        ctx['_approval_decisions'] = approval
        ctx['_last_operator'] = str(request.user)
        execution.context = ctx
        execution.save(update_fields=['context'])
        # 如果 pipeline 处于暂停状态，恢复执行
        if execution.status == PipelineState.PAUSED:
            FlowEngine(execution).resume()
        return api_success(msg='审批通过')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """审批拒绝 — 标记节点为已拒绝"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        reason = request.data.get('reason', '审批拒绝')
        ctx = dict(execution.context or {})
        approval = dict(ctx.get('_approval_decisions', {}))
        approval[node_id] = {'approved': False, 'by': str(request.user),
                             'at': datetime.datetime.now().isoformat(), 'reason': reason}
        ctx['_approval_decisions'] = approval
        ctx['_last_operator'] = str(request.user)
        execution.context = ctx
        execution.save(update_fields=['context'])
        if execution.status == PipelineState.PAUSED:
            FlowEngine(execution).resume()
        return api_success(msg='已拒绝')

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
