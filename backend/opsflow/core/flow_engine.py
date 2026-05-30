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

logger = logging.getLogger(__name__)


class FlowEngine:
    """流程执行引擎 — BambooDjangoRuntime 驱动"""

    def __init__(self, execution):
        self.execution = execution
        self.template = execution.template

    # -- External API --------------------------------------------------------

    def start(self):
        """启动执行，创建 Celery 任务"""
        self.execution.status = "running"
        self.execution.started_at = datetime.datetime.now()
        self.execution.node_status = {}
        self.execution.context = {}
        self.execution.save()
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

    # -- Notification helpers ------------------------------------------------

    def _notify_node(self, node_id, status):
        from opsflow.tasks import notify_node_status

        notify_node_status.delay(self.execution.id, node_id, status)

    def _notify_completed(self):
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"execution_{self.execution.id}",
            {"type": "execution.completed", "status": self.execution.status},
        )
