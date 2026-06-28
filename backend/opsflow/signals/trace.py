"""Trace management — 节点执行轨迹、日志记录、OpsLog 写入

负责 NodeExecutionTrace 的创建/更新/输出捕获，以及
OpsLog 的创建和节点日志文件写入。
"""

import json
import logging

from django.utils import timezone

from bamboo_engine import states

from opsflow.core.trace_logger import NodeTraceLogger
from opsflow.signals.state import _map_bamboo_state
from opsflow.signals.helpers import _get_current_retry_count, _get_node_error, _is_approval_node

logger = logging.getLogger(__name__)


def _resolve_loop_iteration(execution, node_id, retry_count) -> int:
    """Determine loop_iteration for the current signal.

    If the latest trace for (execution, node_id, rc=N) has reached a terminal
    status (FINISHED/FAILED), the engine has started the next loop iteration.
    Returns the new iteration number (existing li + 1).
    Otherwise returns the existing li (normal update path).
    Signals are processed synchronously, so there is no race condition:
    FINISHED is fully written to DB before the next RUNNING fires.
    """
    from opsflow.models import NodeExecutionTrace

    existing = NodeExecutionTrace.objects.filter(
        execution=execution, node_id=node_id, retry_count=retry_count
    ).order_by('-loop_iteration').first()

    if existing and existing.status in ('completed', 'failed'):
        return existing.loop_iteration + 1
    return existing.loop_iteration if existing else 0


def _record_node_trace(execution, node_id, to_state):
    """创建或更新 NodeExecutionTrace 记录"""
    from opsflow.models import NodeExecutionTrace

    retry_count = _get_current_retry_count(execution, node_id)
    loop_it = _resolve_loop_iteration(execution, node_id, retry_count)
    now_iso = timezone.now().isoformat()

    # 从 template_snapshot 中读取 node_type / atom_type
    snapshot = execution.template_snapshot or {}
    tree = snapshot.get('pipeline_tree', {}) or {}
    node_info = {}
    for n in tree.get('nodes', []):
        if n.get('id') == node_id:
            node_info = n
            break

    trace, created = NodeExecutionTrace.objects.get_or_create(
        execution=execution,
        node_id=node_id,
        retry_count=retry_count,
        loop_iteration=loop_it,
        defaults={
            "status": _map_bamboo_state(to_state),
            "status_history": [{"state": _map_bamboo_state(to_state), "at": now_iso}],
            "entered_at": timezone.now() if to_state == states.RUNNING else None,
            "node_type": node_info.get('node_type', ''),
            "node_label": node_info.get('label', ''),
        },
    )

    if not created:
        # 追加状态变更历史
        history = list(trace.status_history or [])
        history.append({"state": _map_bamboo_state(to_state), "at": now_iso})
        trace.status_history = history
        trace.status = _map_bamboo_state(to_state)

        if to_state in (states.FINISHED, states.FAILED):
            trace.exited_at = timezone.now()
            if trace.entered_at:
                delta = trace.exited_at - trace.entered_at
                trace.duration_ms = int(delta.total_seconds() * 1000)
            # 读取 outputs 和 inputs
            trace.outputs = _capture_node_outputs(execution, node_id)
            trace.inputs = _capture_node_inputs(execution, node_id)

            # 审批节点完成 → 暂停 pipeline
            if to_state == states.FINISHED and _is_approval_node(node_id):
                from opsflow.core.flow_engine import FlowEngine
                try:
                    engine = FlowEngine(execution)
                    engine.pause()
                    logger.info("[Signal] approval node %s completed, pipeline paused", node_id)
                except Exception:
                    logger.exception("[Signal] pause after approval failed")

        if to_state == states.FAILED:
            trace.error = _get_node_error(execution, node_id)

        trace.save()

    # 写入日志文件
    tlog = NodeTraceLogger(execution.id)
    tlog.log_state(node_id, "", _map_bamboo_state(to_state))


def _capture_node_inputs(execution, node_id) -> dict:
    """从 pipeline_tree 模板快照中读取节点入参（params）

    引擎只持久化 SPLICE 变量的解析值，PLAIN 类型不存储。
    直接读取 execution.template_snapshot.pipeline_tree.nodes[].params
    获取原始入参，不依赖引擎 ERI。
    """
    try:
        snapshot = execution.template_snapshot or {}
        tree = snapshot.get('pipeline_tree', {}) or {}
        nodes = tree.get('nodes', []) or []
        for node in nodes:
            if node.get('id') == node_id:
                params = node.get('params', {}) or {}
                return dict(params)
    except Exception:
        logger.exception("[Signal] _capture_node_inputs failed")
    return {}


def _capture_node_outputs(execution, node_id) -> dict:
    """读取节点输出

    bamboo-engine 的信号触发在 set_execution_data 之前，
    所以 get_execution_data_outputs 调用时数据尚未持久化。
    从 execution.context['_node_outputs'] 读取（由 _promote_results 写入）。
    """
    try:
        ctx = execution.context or {}
        node_outputs = ctx.get('_node_outputs', {}) or {}
        return node_outputs.get(node_id, {})
    except Exception:
        logger.exception("[Signal] _capture_node_outputs failed")
    return {}


def _write_node_trace_log(execution, node_id, is_failed=False):
    """将节点执行结果写入独立日志文件"""
    from opsflow.models import NodeExecutionTrace

    outputs = _capture_node_outputs(execution, node_id)
    tlog = NodeTraceLogger(execution.id)

    if is_failed:
        error = outputs.get("_error", outputs.get("stderr", ""))
        tlog.log_error(node_id, str(error) if error else "unknown error")
    else:
        tlog.log_output(node_id, outputs)

    # 记录日志文件路径到 trace
    log_path = tlog.get_log_file_path(node_id)
    NodeExecutionTrace.objects.filter(
        execution=execution, node_id=node_id
    ).update(log_file_path=log_path)


def _log_node_result(execution, node_id, is_failed):
    """读取节点输出并记录 OpsLog"""
    from opsflow.models import OpsLog

    outputs = _capture_node_outputs(execution, node_id)

    stderr = outputs.get("stderr", outputs.get("_stderr", ""))
    error = outputs.get("_error", "")
    returncode = outputs.get("returncode", -1 if is_failed else 0)

    # 从 execution context 中获取操作人（手动 retry/skip/force_fail 时记录）
    ctx = execution.context or {}
    approved_by = ctx.get("_last_operator", "")

    OpsLog.objects.create(
        execution=execution,
        step=node_id,
        command="",
        stdout=json.dumps(outputs, ensure_ascii=False, default=str) if outputs else "",
        stderr=str(error) if error else stderr,
        returncode=returncode,
        risk_level="medium" if is_failed else "low",
        approved_by=approved_by,
    )
