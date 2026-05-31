"""State management — 节点状态持久化和状态树增量更新

负责将 bamboo-engine 的节点状态变更写入 FlowExecution 的
node_status（JSONField）和 state_tree（JSONField）。
"""

import logging
from datetime import datetime

from django.utils import timezone

from bamboo_engine import states

logger = logging.getLogger(__name__)


def _update_execution_node_status(execution, node_id, to_state):
    """将节点状态持久化到 FlowExecution.node_status（JSONField）

    覆盖所有 bamboo-engine 状态：READY/RUNNING/FINISHED/FAILED/
    SUSPENDED/REVOKED/BLOCKED，确保 node_status 完整反映节点生命周期。

    使用 execution.context.node_id_map 将 bamboo-engine UUID 映射回
    原始 pipeline_tree 节点 ID（前端 X6 图形 ID），确保节点颜色正确。
    """
    status_map = {
        states.READY: "pending",
        states.RUNNING: "running",
        states.FINISHED: "completed",
        states.FAILED: "failed",
        states.SUSPENDED: "paused",
        states.REVOKED: "cancelled",
        states.BLOCKED: "blocked",
    }
    mapped = status_map.get(to_state)
    if not mapped:
        return

    # 映射 bamboo UUID → 原始 pipeline_tree 节点 ID
    id_map = execution.context.get('node_id_map', {}) if execution.context else {}
    original_id = id_map.get(node_id, node_id)

    ns = dict(execution.node_status or {})
    ns[original_id] = mapped
    execution.node_status = ns
    execution.save(update_fields=["node_status"])


def _update_state_tree(execution, node_id, to_state):
    """增量更新 FlowExecution.state_tree — 时间/耗时/错误详情"""
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
