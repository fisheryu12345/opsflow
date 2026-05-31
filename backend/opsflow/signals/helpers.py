"""Helper functions — 信号处理中使用的工具函数

包含重试次数推断、错误信息提取、审批节点检测等辅助逻辑。
"""

import logging

from bamboo_engine import api as pipeline_api
from pipeline.eri.runtime import BambooDjangoRuntime

logger = logging.getLogger(__name__)


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


def _is_approval_node(node_id) -> bool:
    """通过 bamboo-engine API 检查节点是否为审批节点"""
    try:
        runtime = BambooDjangoRuntime()
        result = pipeline_api.get_execution_data_inputs(runtime, node_id)
        if result.result and result.data:
            inputs = result.data
            if isinstance(inputs, dict) and inputs.get('_atom_type') == 'approval':
                return True
    except Exception:
        pass
    return False
