"""NodeCommandDispatcher — 节点操作调度器

对 bk_sops NodeCommandDispatcher 模式的轻量适配，在 FlowEngine 之上
封装节点级操作 + 轨迹追踪的标准化接口。

所有操作返回 {result: bool, message: str, data: any} 格式。
"""

import logging

from django.utils import timezone

from opsflow.models import FlowExecution, NodeExecutionTrace
from opsflow.core.flow_engine import FlowEngine
from opsflow.core.trace_logger import NodeTraceLogger

logger = logging.getLogger(__name__)


class NodeCommandDispatcher:
    """节点操作调度器

    职责:
      - retry/skip: 调用 FlowEngine 对应方法并追加 Trace 记录
      - get_trace/get_trace_log/get_state_tree: 轨迹查询
    """

    def __init__(self, execution: FlowExecution):
        self.execution = execution
        self.engine = FlowEngine(execution)

    # -- Commands ------------------------------------------------------------

    def retry(self, node_id: str, operator: str = "") -> dict:
        """重试指定失败节点

        1. 查询当前 retry_count，递增
        2. 创建新的 NodeExecutionTrace 记录
        3. 调用 NodeTraceLogger.log_retry()
        4. 委托 FlowEngine.retry()
        """
        # 获取当前重试次数
        last_trace = (
            NodeExecutionTrace.objects.filter(
                execution=self.execution, node_id=node_id
            )
            .order_by("-retry_count")
            .first()
        )
        retry_count = (last_trace.retry_count + 1) if last_trace else 0

        # 写 context 记录重试次数 + 操作人
        ctx = dict(self.execution.context or {})
        retry_map = dict(ctx.get("_retry_counts", {}))
        retry_map[node_id] = retry_count
        ctx["_retry_counts"] = retry_map
        if operator:
            ctx["_last_operator"] = operator
        self.execution.context = ctx
        self.execution.save(update_fields=["context"])

        # 创建新 Trace 记录
        NodeExecutionTrace.objects.create(
            execution=self.execution,
            node_id=node_id,
            retry_count=retry_count,
            node_label=last_trace.node_label if last_trace else "",
            status="retrying",
            status_history=[
                {"state": "retrying", "at": timezone.now().isoformat()}
            ],
        )

        # 写入日志文件
        try:
            tlog = NodeTraceLogger(self.execution.id)
            tlog.log_retry(node_id, retry_count, reason=f"operator: {operator}" if operator else "")
        except Exception:
            pass

        # 委托引擎
        try:
            self.engine.retry(node_id)
        except Exception as e:
            logger.exception("[Dispatcher] retry node %s failed", node_id)
            return {"result": False, "message": f"重试失败: {e}", "data": None}

        return {
            "result": True,
            "message": f"正在重试节点 {node_id} (第 {retry_count} 次)",
            "data": {"node_id": node_id, "retry_count": retry_count},
        }

    def skip(self, node_id: str, operator: str = "") -> dict:
        """跳过指定节点"""
        if operator:
            ctx = dict(self.execution.context or {})
            ctx["_last_operator"] = operator
            self.execution.context = ctx
            self.execution.save(update_fields=["context"])
        try:
            self.engine.skip(node_id)
        except Exception as e:
            logger.exception("[Dispatcher] skip node %s failed", node_id)
            return {"result": False, "message": f"跳过失败: {e}", "data": None}

        return {
            "result": True,
            "message": f"已跳过节点 {node_id}",
            "data": {"node_id": node_id},
        }

    def force_fail(self, node_id: str, operator: str = "", reason: str = "") -> dict:
        """强制标记节点为失败状态"""
        if operator:
            ctx = dict(self.execution.context or {})
            ctx["_last_operator"] = operator
            self.execution.context = ctx
            self.execution.save(update_fields=["context"])
        ex_data = reason or f"force_fail by {operator}" if operator else "force_fail"
        try:
            self.engine.force_fail(node_id, ex_data=ex_data)
        except Exception as e:
            logger.exception("[Dispatcher] force_fail node %s failed", node_id)
            return {"result": False, "message": f"强制失败失败: {e}", "data": None}

        return {
            "result": True,
            "message": f"已强制标记节点 {node_id} 为失败",
            "data": {"node_id": node_id},
        }

    # -- Queries -------------------------------------------------------------

    def get_trace(self, node_id: str) -> dict:
        """查询节点完整轨迹（含所有重试历史）"""
        traces = NodeExecutionTrace.objects.filter(
            execution=self.execution, node_id=node_id
        ).order_by("retry_count").values(
            "node_id", "node_label", "status", "retry_count",
            "duration_ms", "entered_at", "exited_at", "error",
            "status_history", "log_file_path",
        )
        return {"result": True, "data": list(traces)}

    def get_trace_log(self, node_id: str) -> dict:
        """读取节点日志文件内容

        Returns:
            data: 日志内容字符串（原始 JSON Lines 文本）
            文件不存在时 data 为 None
        """
        trace = (
            NodeExecutionTrace.objects.filter(
                execution=self.execution, node_id=node_id
            )
            .order_by("-retry_count")
            .first()
        )
        if not trace or not trace.log_file_path:
            return {"result": False, "message": "日志文件不存在", "data": None}

        import os
        if not os.path.exists(trace.log_file_path):
            return {"result": False, "message": "日志文件未找到", "data": None}

        try:
            with open(trace.log_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"result": True, "data": content}
        except OSError as e:
            return {"result": False, "message": f"读取失败: {e}", "data": None}

    def get_state_tree(self) -> dict:
        """获取完整状态树"""
        return {"result": True, "data": self.execution.state_tree or {}}

    def get_all_traces_summary(self) -> dict:
        """获取执行的所有节点轨迹摘要

        返回 state_tree + traces 列表（不含完整 outputs）
        """
        traces = NodeExecutionTrace.objects.filter(
            execution=self.execution
        ).order_by("entered_at").values(
            "node_id", "node_label", "status", "retry_count",
            "duration_ms", "entered_at", "exited_at", "error",
        )
        return {
            "result": True,
            "data": {
                "state_tree": self.execution.state_tree or {},
                "traces": list(traces),
            },
        }
