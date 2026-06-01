"""Signal handlers — on_post_set_state 接收器和根节点状态管理器

作为信号分发的入口点，将节点状态变更路由到各子模块处理。
"""

import datetime
import logging

from django.dispatch import receiver
from django.utils import timezone

from pipeline.eri.signals import post_set_state
from pipeline.eri.runtime import BambooDjangoRuntime

from bamboo_engine import states, api as pipeline_api
from opsflow.core.states import PipelineState, map_bamboo_node_state, map_pipeline_state
from opsflow.signals.state import _update_execution_node_status, _update_state_tree
from opsflow.signals.trace import _record_node_trace, _log_node_result, _write_node_trace_log
from opsflow.signals.notify import _notify_node_status, _notify_completed
from opsflow.signals.timeout import _update_node_timeout  # Redis 超时追踪

logger = logging.getLogger(__name__)


def _try_webhook(execution, event: str):
    """尝试触发 Webhook 回调（best-effort）"""
    try:
        from opsflow.core.webhook_service import WebhookService
        WebhookService.dispatch(execution, event)
    except Exception:
        logger.exception("[Webhook] dispatch error for execution %s event=%s", execution.id, event)


@receiver(post_set_state)
def on_post_set_state(sender, node_id, to_state, version, root_id, parent_id, loop, **kwargs):
    """BambooDjangoRuntime 节点状态变更信号处理器

    1. 根 pipeline 节点（node_id == root_id）状态变更 → 更新 FlowExecution.status
    2. 子节点进入终态（FINISHED/FAILED）→ 记录 OpsLog + WS 推送
    """
    from opsflow.models import FlowExecution

    pipeline_id = root_id or node_id
    try:
        execution = FlowExecution.objects.get(
            context__contains={"bamboo_pipeline_id": pipeline_id}
        )
    except FlowExecution.DoesNotExist:
        return
    except FlowExecution.MultipleObjectsReturned:
        logger.warning("Multiple FlowExecution found for pipeline %s", pipeline_id)
        return

    if node_id == root_id:
        _handle_root_state_change(execution, to_state)
    else:
        # 映射 bamboo UUID → 原始 pipeline_tree 节点 ID（前端画布使用原始 ID）
        id_map = (execution.context or {}).get('node_id_map', {})
        mapped_node_id = id_map.get(node_id, node_id)

        # 自动重试拦截：失败时先检查是否有自动重试策略
        if to_state == states.FAILED:
            from opsflow.core.auto_retry import dispatch_auto_retry
            if dispatch_auto_retry(execution, node_id):
                # 已派发自动重试，跳过正常失败处理
                return

        # 更新 DB 中的 node_status（持久化，页面刷新后可恢复）
        _update_execution_node_status(execution, node_id, to_state)
        # 状态树快照（增量更新，使用 bamboo UUID 内部追踪）
        _update_state_tree(execution, node_id, to_state)
        # 节点执行轨迹记录
        _record_node_trace(execution, node_id, to_state)
        # Redis 超时追踪（RUNNING→添加到期，FINISHED/FAILED→移除）
        _update_node_timeout(execution, node_id, to_state)
        # 记录当前正在执行的节点（用于前端高亮 + API 查询）
        if to_state == states.RUNNING:
            execution.current_node = mapped_node_id if mapped_node_id != node_id else node_id
            execution.save(update_fields=["current_node"])
        if to_state in (states.FINISHED, states.FAILED):
            _log_node_result(execution, node_id, is_failed=(to_state == states.FAILED))
            _write_node_trace_log(execution, node_id, is_failed=(to_state == states.FAILED))
            # WS 推送使用映射后的原始节点 ID（前端通过 getCellById 查找）
            _notify_node_status(execution, mapped_node_id, to_state.lower())
        elif to_state == states.RUNNING:
            _notify_node_status(execution, mapped_node_id, "running")


def _handle_root_state_change(execution, to_state):
    """处理根 pipeline 节点状态变化 — 更新 FlowExecution.status"""
    target = map_pipeline_state(to_state)
    if target is None:
        return

    if target == PipelineState.COMPLETED:
        execution.status = PipelineState.COMPLETED
        execution.ended_at = datetime.datetime.now()
        execution.save(update_fields=["status", "ended_at"])
        _notify_completed(execution)
        # Webhook 回调
        _try_webhook(execution, 'completed')
        logger.info("[Signal] pipeline %s completed", execution.id)

    elif target == PipelineState.FAILED:
        execution.status = PipelineState.FAILED
        execution.ended_at = datetime.datetime.now()
        execution.save(update_fields=["status", "ended_at"])
        # 触发失败节点回滚
        try:
            from opsflow.core.flow_engine import FlowEngine
            engine = FlowEngine(execution)
            engine.rollback_failed_nodes()
        except Exception:
            logger.exception("[Signal] rollback_failed_nodes error for execution %s", execution.id)
        _notify_completed(execution)
        # Webhook 回调
        _try_webhook(execution, 'failed')
        logger.info("[Signal] pipeline %s failed", execution.id)

    elif target == PipelineState.CANCELLED:
        execution.status = PipelineState.CANCELLED
        execution.ended_at = datetime.datetime.now()
        execution.save(update_fields=["status", "ended_at"])
        _notify_completed(execution)

    elif target == PipelineState.PAUSED:
        execution.status = PipelineState.PAUSED
        execution.save(update_fields=["status"])

    elif target == PipelineState.RUNNING:
        execution.status = PipelineState.RUNNING
        execution.save(update_fields=["status"])
