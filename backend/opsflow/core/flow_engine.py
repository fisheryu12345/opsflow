"""Flow Execution Engine — BambooDjangoRuntime + bamboo_engine.api

替换了旧的自定义 Pipeline Tree 解释器（手动遍历 activities/gateways/flows、
Redis 计数器 ConvergeGateway、Celery group ParallelGateway），改用
bamboo-pipeline 的 ERI 运行时 BambooDjangoRuntime 驱动执行。

关键变更：
  - run() 使用 bamboo_engine.api.run_pipeline() 委托执行
  - 节点状态追踪通过 post_set_state 信号异步完成（见 signals.py）
  - resume/retry/skip 委托给 bamboo_engine.api
  - pause 委托给 bamboo_engine.api.pause_pipeline()
"""

import datetime
import logging

from bamboo_engine import api as pipeline_api
from pipeline.eri.runtime import BambooDjangoRuntime

from opsflow.core.bamboo_builder import build_bamboo_pipeline
from opsflow.core.executors.factory import AtomExecutorFactory
from opsflow.models import OpsLog

logger = logging.getLogger(__name__)


class FlowEngine:
    """流程执行引擎 — BambooDjangoRuntime 驱动"""

    def __init__(self, execution):
        self.execution = execution
        self.template = execution.template

    # -- External API --------------------------------------------------------

    def start(self, sync=False):
        """启动执行

        Args:
            sync: True=直接同步执行（不依赖 Celery/bamboo-engine），
                  False=创建 Celery 任务异步执行（默认）
        """
        self.execution.status = "running"
        self.execution.started_at = datetime.datetime.now()
        self.execution.node_status = {}
        self.execution.context = {}
        self.execution.save()
        if sync:
            self.run_sync()
        else:
            from opsflow.tasks import execute_pipeline_task

            execute_pipeline_task.delay(self.execution.id)

    def pause(self):
        """暂停执行 — 委托给 BambooDjangoRuntime"""
        bamboo_pipeline_id = self.execution.context.get("bamboo_pipeline_id")
        if bamboo_pipeline_id:
            runtime = BambooDjangoRuntime()
            result = pipeline_api.pause_pipeline(runtime, bamboo_pipeline_id)
            if not result.result:
                logger.error("[FlowEngine] pause failed: %s", result.message)
        self.execution.status = "paused"
        self.execution.save(update_fields=["status"])

    def resume(self):
        """恢复暂停的执行 — 委托给 BambooDjangoRuntime"""
        bamboo_pipeline_id = self.execution.context.get("bamboo_pipeline_id")
        if not bamboo_pipeline_id:
            logger.error("[FlowEngine] resume: no bamboo_pipeline_id in context")
            return
        runtime = BambooDjangoRuntime()
        result = pipeline_api.resume_pipeline(runtime, bamboo_pipeline_id)
        if not result.result:
            logger.error("[FlowEngine] resume failed: %s", result.message)
            return
        self.execution.status = "running"
        self.execution.save(update_fields=["status"])

    def retry(self, node_id):
        """重试指定失败节点 — 委托给 BambooDjangoRuntime"""
        runtime = BambooDjangoRuntime()
        result = pipeline_api.retry_node(runtime, node_id)
        if not result.result:
            logger.error("[FlowEngine] retry node %s failed: %s", node_id, result.message)
        else:
            node_status = self.execution.node_status or {}
            node_status[node_id] = "retrying"
            self.execution.node_status = node_status
            self.execution.status = "running"
            self.execution.save(update_fields=["node_status", "status"])

    def skip(self, node_id):
        """跳过指定失败节点 — 委托给 BambooDjangoRuntime"""
        runtime = BambooDjangoRuntime()
        result = pipeline_api.skip_node(runtime, node_id)
        if not result.result:
            logger.error("[FlowEngine] skip node %s failed: %s", node_id, result.message)
        else:
            node_status = self.execution.node_status or {}
            node_status[node_id] = "skipped"
            self.execution.node_status = node_status
            self.execution.save(update_fields=["node_status"])

    def cancel(self):
        """取消终止执行 — 撤销 pipeline 并标记为 cancelled"""
        bamboo_pipeline_id = self.execution.context.get("bamboo_pipeline_id")
        if bamboo_pipeline_id:
            runtime = BambooDjangoRuntime()
            result = pipeline_api.revoke_pipeline(runtime, bamboo_pipeline_id)
            if not result.result:
                logger.error("[FlowEngine] cancel failed: %s", result.message)
        self.execution.status = "cancelled"
        self.execution.ended_at = datetime.datetime.now()
        self.execution.save(update_fields=["status", "ended_at"])
        self._send_ws_completed()
        logger.info(
            "[FlowEngine] execution %s cancelled",
            self.execution.id,
        )

    # -- Run ------------------------------------------------------------------

    def run(self):
        """执行 Pipeline（由 Celery worker 调用）

        构建 bamboo-engine 标准 Pipeline Tree 后调用 api.run_pipeline()。
        run_pipeline 异步调度节点执行到 Celery er_execute/er_schedule 队列，
        状态追踪由 signals.py 中的 post_set_state 信号处理器完成。
        """
        try:
            pipeline = build_bamboo_pipeline(self.template)
            bamboo_pipeline_id = pipeline.get("id", "")

            self.execution.context["bamboo_pipeline_id"] = bamboo_pipeline_id
            self.execution.context["bamboo_pipeline"] = pipeline
            self.execution.save(update_fields=["context"])

            runtime = BambooDjangoRuntime()
            result = pipeline_api.run_pipeline(runtime=runtime, pipeline=pipeline)

            if not result.result:
                logger.error("[FlowEngine] run_pipeline failed: %s", result.message)
                self.execution.status = "failed"
                self.execution.ended_at = datetime.datetime.now()
                self.execution.save()
                self._notify_completed()
                return

            logger.info(
                "[FlowEngine] pipeline %s dispatched (async execution via er_execute queue)",
                bamboo_pipeline_id,
            )

        except Exception as e:
            logger.exception("[FlowEngine] run failed")
            self.execution.status = "failed"
            self.execution.ended_at = datetime.datetime.now()
            self.execution.save()
            self._notify_completed()

    # -- Run (sync) -----------------------------------------------------------

    def run_sync(self):
        """直接同步执行 Pipeline（不依赖 Celery / bamboo-engine）

        从模板 pipeline_tree 读取 nodes + edges，拓扑排序后逐个调用
        AtomExecutorFactory.execute_atom() 执行，每步更新 DB 并推送
        WebSocket 通知（best-effort）。
        """
        tree = self.template.pipeline_tree
        if not tree:
            logger.error("[FlowEngine] run_sync: template has no pipeline_tree")
            self.execution.status = "failed"
            self.execution.ended_at = datetime.datetime.now()
            self.execution.save()
            return

        raw_nodes = tree.get("nodes", [])
        edges = tree.get("edges", [])
        nodes_by_id = {n["id"]: n for n in raw_nodes}

        # --- topological sort ---
        in_degree = {nid: 0 for nid in nodes_by_id}
        adj = {nid: [] for nid in nodes_by_id}
        for e in edges:
            f, t = e.get("from"), e.get("to")
            if f in adj and t in in_degree:
                adj[f].append(t)
                in_degree[t] = in_degree.get(t, 0) + 1

        queue = [nid for nid, d in in_degree.items() if d == 0]
        order = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for nxt in adj.get(nid, []):
                in_degree[nxt] = in_degree.get(nxt, 0) - 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        # --- execute nodes in order ---
        for node_id in order:
            node = nodes_by_id[node_id]
            atom_type = node.get("atom_type")
            ntype = node.get("type", "")
            # skip structural nodes (gateways / events)
            if not atom_type or ntype in ("start_event", "end_event"):
                continue

            self._update_node(node_id, "running")
            self._send_ws_node_status(node_id, "running")

            inputs = dict(node.get("params", {}))
            inputs.update({
                "_atom_type": atom_type,
                "_execution_id": self.execution.id,
                "_node_id": node_id,
            })

            result = AtomExecutorFactory.execute_atom(
                atom_type, inputs, self.template.target_hosts
            )

            if result.success:
                self._update_node(node_id, "completed")
                self._send_ws_node_status(node_id, "completed")
                logger.info(
                    "[FlowEngine] node %s (%s) completed", node_id, atom_type
                )
            else:
                logger.error(
                    "[FlowEngine] node %s (%s) failed: %s",
                    node_id, atom_type, result.error,
                )
                self._update_node(node_id, "failed")
                self._send_ws_node_status(node_id, "failed")
                self.execution.status = "failed"
                self.execution.ended_at = datetime.datetime.now()
                self.execution.save()
                self._send_ws_completed()
                OpsLog.objects.create(
                    execution=self.execution,
                    status="failed",
                    step=node.get("label", node_id),
                    message=result.error or "Node execution failed",
                )
                return

        # all nodes completed successfully
        self.execution.status = "completed"
        self.execution.ended_at = datetime.datetime.now()
        self.execution.save()
        self._send_ws_completed()
        logger.info(
            "[FlowEngine] execution %s completed (sync)",
            self.execution.id,
        )

    def _update_node(self, node_id: str, status: str):
        """更新节点状态到 DB"""
        ns = dict(self.execution.node_status or {})
        ns[node_id] = status
        self.execution.node_status = ns
        if status == "running":
            self.execution.current_node = node_id
        self.execution.save(update_fields=["node_status", "current_node"])

    # -- Notification helpers ------------------------------------------------

    def _notify_node(self, node_id, status):
        """推送节点状态通知 — 通过 Celery 任务"""
        from opsflow.tasks import notify_node_status

        notify_node_status.delay(self.execution.id, node_id, status)

    def _notify_completed(self):
        """推送执行完成通知 — 通过 channel layer"""
        self._send_ws_completed()

    def _send_ws_node_status(self, node_id, status):
        """直接推送节点状态到 WebSocket（best-effort，不抛异常）

        不能使用 async_to_sync，理由见 opsflow/tasks.py notify_node_status。
        run_sync 模式下直接从 Celery worker 调用此方法，需手动管理事件循环。
        """
        try:
            from channels.layers import get_channel_layer
            from opsflow.tasks import run_async

            channel_layer = get_channel_layer()
            if channel_layer:
                run_async(
                    channel_layer.group_send(
                        f"execution_{self.execution.id}",
                        {
                            "type": "node.status",
                            "node_id": node_id,
                            "status": status,
                        },
                    )
                )
        except Exception:
            logger.debug(
                "[FlowEngine] channel layer unavailable, skipped WS notification"
            )

    def _send_ws_completed(self):
        """推送执行完成通知到 WebSocket（best-effort，不抛异常）

        不能使用 async_to_sync，理由见 opsflow/tasks.py notify_node_status。
        """
        try:
            from channels.layers import get_channel_layer
            from opsflow.tasks import run_async

            channel_layer = get_channel_layer()
            if channel_layer:
                run_async(
                    channel_layer.group_send(
                        f"execution_{self.execution.id}",
                        {
                            "type": "execution.completed",
                            "status": self.execution.status,
                        },
                    )
                )
        except Exception:
            logger.debug(
                "[FlowEngine] channel layer unavailable, skipped WS notification"
            )
