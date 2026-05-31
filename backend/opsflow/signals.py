"""pipeline 信号处理器 — 追踪 BambooDjangoRuntime ERI 状态变更

通过 post_set_state 信号（pipeline.eri.signals）监听 BambooDjangoRuntime
的节点状态变更，同步更新 FlowExecution 状态并记录 OpsLog。

信号发送参数: node_id, to_state, version, root_id, parent_id, loop

使用框架 API（get_execution_data_outputs）读取节点数据而非直接查询 ERI 模型，
确保与 bamboo-engine 数据层保持兼容。
"""

import datetime
import json
import logging

from django.dispatch import receiver
from django.utils import timezone

from pipeline.eri.signals import post_set_state
from pipeline.eri.runtime import BambooDjangoRuntime

from bamboo_engine import states, api as pipeline_api
from opsflow.core.states import PipelineState, NodeState, map_bamboo_node_state

logger = logging.getLogger(__name__)


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
        # 更新 DB 中的 node_status（持久化，页面刷新后可恢复）
        _update_execution_node_status(execution, node_id, to_state)
        # 状态树快照（增量更新）
        _update_state_tree(execution, node_id, to_state)
        # 节点执行轨迹记录
        _record_node_trace(execution, node_id, to_state)
        if to_state in (states.FINISHED, states.FAILED):
            _log_node_result(execution, node_id, is_failed=(to_state == states.FAILED))
            _write_node_trace_log(execution, node_id, is_failed=(to_state == states.FAILED))
            _notify_node_status(execution, node_id, to_state.lower())
        elif to_state == states.RUNNING:
            _notify_node_status(execution, node_id, "running")


def _handle_root_state_change(execution, to_state):
    """处理根 pipeline 节点状态变化 — 更新 FlowExecution.status"""
    if to_state == states.FINISHED:
        execution.status = "completed"
        execution.ended_at = datetime.datetime.now()
        execution.save(update_fields=["status", "ended_at"])
        _notify_completed(execution)
        logger.info("[Signal] pipeline %s completed", execution.id)

    elif to_state == states.FAILED:
        execution.status = "failed"
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
        logger.info("[Signal] pipeline %s failed", execution.id)

    elif to_state == states.REVOKED:
        execution.status = "cancelled"
        execution.ended_at = datetime.datetime.now()
        execution.save(update_fields=["status", "ended_at"])
        _notify_completed(execution)

    elif to_state == states.SUSPENDED:
        execution.status = "paused"
        execution.save(update_fields=["status"])

    elif to_state == states.RUNNING:
        execution.status = "running"
        execution.save(update_fields=["status"])


def _update_execution_node_status(execution, node_id, to_state):
    """将节点状态持久化到 FlowExecution.node_status（JSONField）"""
    status_map = {
        states.FINISHED: "completed",
        states.FAILED: "failed",
        states.RUNNING: "running",
    }
    mapped = status_map.get(to_state)
    if not mapped:
        return
    ns = dict(execution.node_status or {})
    ns[node_id] = mapped
    execution.node_status = ns
    execution.save(update_fields=["node_status"])


def _update_state_tree(execution, node_id, to_state):
    """增量更新 FlowExecution.state_tree — 时间/耗时/错误详情"""
    from datetime import datetime

    STATUS_MAP = {
        states.FINISHED: "completed",
        states.FAILED: "failed",
        states.RUNNING: "running",
        states.REVOKED: "cancelled",
        states.SUSPENDED: "paused",
    }
    mapped = STATUS_MAP.get(to_state)
    if not mapped:
        return

    tree = dict(execution.state_tree or {})
    entry = dict(tree.get(node_id, {}))

    entry["state"] = mapped
    now_iso = timezone.now().isoformat()

    if mapped == "running":
        entry["entered_at"] = now_iso
        # 清除前次结束时间（重试时重置）
        entry.pop("exited_at", None)
        entry.pop("duration_ms", None)
    elif mapped in ("completed", "failed", "cancelled"):
        entry["exited_at"] = now_iso
        if entry.get("entered_at"):
            try:
                entered = datetime.fromisoformat(entry["entered_at"])
                delta = timezone.now() - entered
                entry["duration_ms"] = int(delta.total_seconds() * 1000)
            except (ValueError, TypeError):
                pass

    tree[node_id] = entry
    execution.state_tree = tree
    execution.save(update_fields=["state_tree"])


def _get_current_retry_count(execution, node_id) -> int:
    """从 context 或现有 Trace 记录推断当前重试次数"""
    # 优先从 context 读取（FlowEngine.retry 写入）
    ctx = execution.context or {}
    retry_map = ctx.get("_retry_counts", {})
    count = retry_map.get(node_id, 0)
    if count > 0:
        return count
    # fallback: 查询现有 Trace 记录的最大 retry_count
    from opsflow.models import NodeExecutionTrace
    last = (
        NodeExecutionTrace.objects.filter(execution=execution, node_id=node_id)
        .order_by("-retry_count")
        .first()
    )
    return last.retry_count if last else 0


def _get_node_error(execution, node_id) -> str:
    """从 context 或 outputs 提取节点错误信息"""
    ctx = execution.context or {}
    node_ctx = ctx.get(node_id, {})
    if isinstance(node_ctx, dict):
        error = node_ctx.get("error") or node_ctx.get("stderr") or ""
        if error:
            return error
    # fallback: 搜索 NodeExecutionTrace 最近一次 output
    from opsflow.models import NodeExecutionTrace
    trace = (
        NodeExecutionTrace.objects.filter(execution=execution, node_id=node_id)
        .order_by("-retry_count")
        .first()
    )
    if trace and trace.error:
        return trace.error
    return ""


def _record_node_trace(execution, node_id, to_state):
    """创建或更新 NodeExecutionTrace 记录"""
    from opsflow.core.trace_logger import NodeTraceLogger
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

        if to_state == states.FAILED:
            trace.error = _get_node_error(execution, node_id)

        trace.save()

    # 写入日志文件
    tlog = NodeTraceLogger(execution.id)
    tlog.log_state(node_id, "", _map_bamboo_state(to_state))


def _map_bamboo_state(to_state) -> str:
    """将 bamboo-engine 状态映射为简洁字符串"""
    mapping = {
        states.FINISHED: "completed",
        states.FAILED: "failed",
        states.RUNNING: "running",
        states.READY: "pending",
        states.REVOKED: "cancelled",
        states.SUSPENDED: "paused",
        states.BLOCKED: "blocked",
    }
    return mapping.get(to_state, str(to_state).lower())


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
    from opsflow.core.trace_logger import NodeTraceLogger
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

    OpsLog.objects.create(
        execution=execution,
        step=node_id,
        command="",
        stdout=json.dumps(outputs, ensure_ascii=False, default=str) if outputs else "",
        stderr=str(error) if error else stderr,
        returncode=returncode,
        risk_level="medium" if is_failed else "low",
    )


def _notify_node_status(execution, node_id, status):
    """推送节点状态变更到 WebSocket"""
    from opsflow.tasks import notify_node_status

    notify_node_status.delay(execution.id, node_id, status)


def _notify_completed(execution):
    """推送流程完成通知到 WebSocket

    使用 tasks.run_async 统一处理事件循环兼容性，避免在 Celery gevent
    工作线程中直接使用 asyncio.new_event_loop() 导致 "Cannot run the
    event loop while another loop is running" 错误。
    """
    from channels.layers import get_channel_layer
    from opsflow.tasks import run_async

    channel_layer = get_channel_layer()
    run_async(
        channel_layer.group_send(
            f"execution_{execution.id}",
            {"type": "execution.completed", "status": execution.status},
        )
    )
