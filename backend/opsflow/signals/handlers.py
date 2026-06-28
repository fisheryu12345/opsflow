"""Signal handlers — on_post_set_state 接收器和根节点状态管理器

作为信号分发的入口点，将节点状态变更路由到各子模块处理。
节点着色通过 WebSocket 实时推送 NODE_STATUS 消息驱动，
回退方案为 API 轮询（通过 node_status / trace_summary）。
"""

import logging

from django.utils import timezone

from django.dispatch import receiver

from pipeline.eri.signals import post_set_state

from bamboo_engine import states, api as pipeline_api
from opsflow.core.states import PipelineState, map_bamboo_node_state, map_pipeline_state
from opsflow.signals.state import _update_execution_node_status, _update_state_tree
from opsflow.signals.trace import _record_node_trace, _log_node_result, _write_node_trace_log
from opsflow.signals.timeout import _update_node_timeout  # Redis 超时追踪

logger = logging.getLogger(__name__)


def _safe_signal_handler(func, execution, node_id, to_state):
    """安全执行信号处理函数，异常时仅记录日志不阻断后续处理器"""
    try:
        func(execution, node_id, to_state)
    except Exception:
        logger.exception("[Signal] %s error exec=%s node=%s", func.__name__, execution.id, node_id)


def _push_node_status_via_ws(execution, node_id):
    """通过 WebSocket 实时推送节点状态到前端

    在 DB 持久化完成后调用，使用 ws_push.push_to_user() 推送到 user_{id} 组，
    前端 WebSocketService 收到 topic="node_status" 后分发给 ExecutionDetail 页面。
    """
    if not execution.created_by_id:
        return
    status = (execution.node_status or {}).get(node_id, '')
    if not status:
        return
    from application.ws_push import push_to_user
    push_to_user(
        execution.created_by_id,
        "node_status",
        "update",
        {
            "execution_id": execution.id,
            "node_id": node_id,
            "status": status,
        },
    )


def _try_webhook(execution, event: str):
    """尝试触发 Webhook 回调（best-effort）"""
    try:
        from opsflow.core.webhook_service import WebhookService
        WebhookService.dispatch(execution, event)
    except Exception:
        logger.exception("[Webhook] dispatch error for execution %s event=%s", execution.id, event)


@receiver(post_set_state)
def on_post_set_state(sender, node_id, to_state, version, root_id, parent_id, loop, **kwargs):
    """BambooDjangoRuntime 节点状态变更信号处理器"""
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
        if to_state == states.FAILED:
            from opsflow.core.auto_retry import dispatch_auto_retry
            if dispatch_auto_retry(execution, node_id):
                return

        signal_steps = [
            _update_execution_node_status,
            _update_state_tree,
            _record_node_trace,
            _update_node_timeout,
        ]
        for step_func in signal_steps:
            _safe_signal_handler(step_func, execution, node_id, to_state)

        # 实时推送节点状态到前端 WebSocket — 不阻塞后续处理
        _push_node_status_via_ws(execution, node_id)

        if to_state == states.RUNNING:
            try:
                execution.current_node = node_id
                execution.save(update_fields=["current_node"])
            except Exception:
                logger.warning("[Signal] current_node save failed (non-critical) exec=%s node=%s", execution.id, node_id)
        if to_state in (states.FINISHED, states.FAILED):
            try:
                _log_node_result(execution, node_id, is_failed=(to_state == states.FAILED))
            except Exception:
                logger.exception("[Signal] _log_node_result error exec=%s node=%s", execution.id, node_id)
            try:
                _write_node_trace_log(execution, node_id, is_failed=(to_state == states.FAILED))
            except Exception:
                logger.exception("[Signal] _write_node_trace_log error exec=%s node=%s", execution.id, node_id)


def _handle_root_state_change(execution, to_state):
    """处理根 pipeline 节点状态变化 — 更新 FlowExecution.status + 清扫 node_status"""
    target = map_pipeline_state(to_state)
    if target is None:
        return

    if target == PipelineState.COMPLETED:
        execution.status = PipelineState.COMPLETED
        execution.ended_at = timezone.now()
        _sweep_node_status(execution, "completed")
        execution.save(update_fields=["status", "ended_at", "node_status"])
        _try_webhook(execution, 'completed')
        logger.info("[Signal] pipeline %s completed", execution.id)

    elif target == PipelineState.FAILED:
        execution.status = PipelineState.FAILED
        execution.ended_at = timezone.now()
        _sweep_node_status(execution, "failed")
        execution.save(update_fields=["status", "ended_at", "node_status"])
        _try_webhook(execution, 'failed')
        logger.info("[Signal] pipeline %s failed", execution.id)

    elif target == PipelineState.CANCELLED:
        execution.status = PipelineState.CANCELLED
        execution.ended_at = timezone.now()
        _sweep_node_status(execution, "cancelled")
        execution.save(update_fields=["status", "ended_at", "node_status"])

    elif target == PipelineState.PAUSED:
        execution.status = PipelineState.PAUSED
        execution.save(update_fields=["status"])

    elif target == PipelineState.RUNNING:
        execution.status = PipelineState.RUNNING
        execution.save(update_fields=["status"])


def _sweep_node_status(execution, terminal_status):
    """清扫 node_status：将所有仍为 running 的节点置为终态

    流程已完成但个别节点的信号因时序竞争或并发原因未更新到终态时，
    批量补全确保前端计数准确。
    前端下次 API 轮询时自动获取更新后的 node_status。
    """
    ns = dict(execution.node_status or {})
    changed = False
    for k, v in ns.items():
        if v in ("running", "finished"):
            ns[k] = terminal_status
            changed = True
    if changed:
        execution.node_status = ns
