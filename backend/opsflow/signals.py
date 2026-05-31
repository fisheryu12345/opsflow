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

from pipeline.eri.signals import post_set_state
from pipeline.eri.runtime import BambooDjangoRuntime

from bamboo_engine import states, api as pipeline_api

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
        if to_state in (states.FINISHED, states.FAILED):
            _log_node_result(execution, node_id, is_failed=(to_state == states.FAILED))
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
        _notify_completed(execution)
        logger.info("[Signal] pipeline %s failed", execution.id)

    elif to_state == states.REVOKED:
        execution.status = "failed"
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
