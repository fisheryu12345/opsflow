"""Execution Approval — 审批/拒绝端点 Mixin"""

import datetime

from rest_framework.decorators import action

from opsflow.core.flow_engine import FlowEngine
from opsflow.core.states import PipelineState
from opsflow.core.error_codes import ErrorCodes, api_success, api_error


class ExecutionApprovalMixin:
    """审批端点混入（approve/reject/pending_approval）"""

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

    def _record_approval_decision(self, execution, node_id, user, decision_data):
        """记录审批决策到 context 并恢复执行（approve/reject 共享）"""
        ctx = dict(execution.context or {})
        approval = dict(ctx.get('_approval_decisions', {}))
        approval[node_id] = {
            'by': str(user),
            'at': datetime.datetime.now().isoformat(),
            **decision_data,
        }
        ctx['_approval_decisions'] = approval
        ctx['_last_operator'] = str(user)
        execution.context = ctx
        execution.save(update_fields=['context'])
        if execution.status == PipelineState.PAUSED:
            FlowEngine(execution).resume()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """审批通过 — 标记节点为已审批并恢复执行"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        comment = request.data.get('comment', '')
        self._record_approval_decision(execution, node_id, request.user,
                                       {'approved': True, 'comment': comment})
        return api_success(msg='审批通过')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """审批拒绝 — 标记节点为已拒绝"""
        execution = self.get_object()
        node_id = request.data.get('node_id', execution.current_node)
        if not node_id:
            return api_error(ErrorCodes.NODE_ID_REQUIRED)
        reason = request.data.get('reason', '审批拒绝')
        self._record_approval_decision(execution, node_id, request.user,
                                       {'approved': False, 'reason': reason})
        return api_success(msg='已拒绝')
