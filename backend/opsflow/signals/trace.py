"""Trace management — 节点执行轨迹、日志记录、OpsLog 写入

负责 NodeExecutionTrace 的创建/更新/输出捕获，以及
OpsLog 的创建和节点日志文件写入。
"""

import json
import logging

from django.utils import timezone

from bamboo_engine import states, api as pipeline_api
from pipeline.eri.runtime import BambooDjangoRuntime

from opsflow.core.trace_logger import NodeTraceLogger
from opsflow.signals.state import _map_bamboo_state
from opsflow.signals.helpers import _get_current_retry_count, _get_node_error, _is_approval_node

logger = logging.getLogger(__name__)


def _record_node_trace(execution, node_id, to_state):
    """创建或更新 NodeExecutionTrace 记录"""
    from opsflow.models import NodeExecutionTrace

    retry_count = _get_current_retry_count(execution, node_id)
    now_iso = timezone.now().isoformat()

    trace, created = NodeExecutionTrace.objects.get_or_create(
        execution=execution,
        node_id=node_id,
        retry_count=retry_count,
        defaults={
            "status": _map_bamboo_state(to_state),
            "status_history": [{"state": _map_bamboo_state(to_state), "at": now_iso}],
            "entered_at": timezone.now() if to_state == states.RUNNING else None,
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
            # 尝试读取 outputs
            trace.outputs = _capture_node_outputs(execution, node_id)

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


def _capture_node_outputs(execution, node_id) -> dict:
    """通过 bamboo_engine API 读取节点输出"""
    try:
        runtime = BambooDjangoRuntime()
        result = pipeline_api.get_execution_data_outputs(runtime, node_id)
        if result.result and result.data:
            raw = result.data
            if isinstance(raw, dict) and "outputs" in raw:
                return raw["outputs"]
            return raw if isinstance(raw, dict) else {}
    except Exception:
        logger.exception("[Signal] get_execution_data_outputs failed for node %s", node_id)
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
    """通过 bamboo_engine.api.get_execution_data_outputs 读取节点输出并记录 OpsLog"""
    from opsflow.models import OpsLog

    outputs = {}
    try:
        runtime = BambooDjangoRuntime()
        result = pipeline_api.get_execution_data_outputs(runtime, node_id)
        if result.result and result.data:
            # result.data 格式: {"outputs": {"key": value, ...}}
            raw = result.data
            if isinstance(raw, dict) and "outputs" in raw:
                outputs = raw["outputs"]
            else:
                outputs = raw
    except Exception:
        logger.exception("[Signal] get_execution_data_outputs failed for node %s", node_id)

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
