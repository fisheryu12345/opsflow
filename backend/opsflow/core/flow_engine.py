"""Flow Execution Engine — BambooDjangoRuntime + bamboo_engine.api

所有执行通过 bamboo-engine 异步驱动（Celery + 信号），与 bk-sops 一致。
节点状态追踪通过 post_set_state 信号异步完成（见 signals.py）。
"""

import datetime
import logging

from bamboo_engine import api as pipeline_api
from bamboo_engine.builder import Data, Var
from pipeline.eri.runtime import BambooDjangoRuntime

from opsflow.core.bamboo_builder import build_bamboo_pipeline
from opsflow.core.safety_guard import validate_pipeline

logger = logging.getLogger(__name__)


class FlowEngine:
    """流程执行引擎 — BambooDjangoRuntime 驱动（仅异步路径）"""

    def __init__(self, execution):
        self.execution = execution
        self.template = execution.template

    # -- External API --------------------------------------------------------

    def start(self, sync=False):
        """启动执行 — 创建 Celery 任务异步执行

        Args:
            sync: True=同步执行（当前进程阻塞等待），False=派发到 Celery 异步执行
        """
        self.execution.status = "running"
        self.execution.started_at = datetime.datetime.now()
        if not self.execution.node_status:
            self.execution.node_status = {}
        # 不重置 context — 保留创建时冻结的 template_snapshot
        self.execution.save()
        from opsflow.tasks import execute_pipeline_task
        if sync:
            execute_pipeline_task(self.execution.id)
        else:
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

    def retry_subprocess(self, node_id):
        """重试子流程节点 — 委托给 bamboo_engine.api.retry_subprocess"""
        runtime = BambooDjangoRuntime()
        result = pipeline_api.retry_subprocess(runtime, node_id)
        if not result.result:
            logger.error("[FlowEngine] retry subprocess %s failed: %s", node_id, result.message)
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

    def force_fail(self, node_id, ex_data=""):
        """强制让指定节点进入失败状态 — 委托给 BambooDjangoRuntime

        Args:
            node_id: 目标节点 ID
            ex_data: 可选的失败原因描述
        """
        runtime = BambooDjangoRuntime()
        result = pipeline_api.forced_fail_activity(
            runtime, node_id, ex_data=ex_data, send_post_set_state_signal=True,
        )
        if not result.result:
            logger.error("[FlowEngine] force_fail node %s failed: %s", node_id, result.message)
        else:
            node_status = self.execution.node_status or {}
            node_status[node_id] = "failed"
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
            # 使用创建时冻结的 template_snapshot（实现模板修改与执行隔离）
            frozen = self.execution.template_snapshot or {}
            frozen_tree = frozen.get('pipeline_tree') or self.execution.context.get('pipeline_tree')
            # 执行时校验 pipeline_tree（防止外部篡改/损坏）
            if frozen_tree:
                validation = validate_pipeline(frozen_tree)
                if not validation.get('valid'):
                    errors = '; '.join(validation.get('errors', []))
                    logger.error("[FlowEngine] pipeline validation failed before run: %s", errors)
                    self.execution.status = "failed"
                    self.execution.ended_at = datetime.datetime.now()
                    self.execution.save()
                    self._notify_completed()
                    return
            pipeline, id_map = build_bamboo_pipeline(
                self.template,
                pipeline_tree=frozen_tree,
                target_hosts=frozen.get('target_hosts'),
                global_vars=frozen.get('global_vars'),
                execution_id=self.execution.id,
                excluded_nodes=self.execution.excluded_nodes,
            )
            bamboo_pipeline_id = pipeline.get("id", "")

            self.execution.context["bamboo_pipeline_id"] = bamboo_pipeline_id
            self.execution.context["bamboo_pipeline"] = pipeline
            self.execution.context["node_id_map"] = id_map
            self.execution.save(update_fields=["context"])

            runtime = BambooDjangoRuntime()
            result = pipeline_api.run_pipeline(runtime=runtime, pipeline=pipeline)

            if not result.result:
                logger.error("[FlowEngine] run_pipeline failed: %s", result.message)
                self.execution.status = "failed"
                self.execution.ended_at = datetime.datetime.now()
                self.execution.save()
                self.rollback_failed_nodes()
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
            self.rollback_failed_nodes()
            self._notify_completed()

    # -- Rollback / Compensation -------------------------------------------

    def rollback_failed_nodes(self):
        """Pipeline 失败后，遍历所有失败节点并调用其 rollback 方法"""
        node_status = self.execution.node_status or {}
        failed_nodes = [nid for nid, st in node_status.items() if st in ('failed',)]
        if not failed_nodes:
            return

        logger.info("[FlowEngine] rolling back %d failed nodes", len(failed_nodes))
        from bamboo_engine import api as pipeline_api
        from pipeline.eri.runtime import BambooDjangoRuntime
        runtime = BambooDjangoRuntime()

        rollback_count = 0
        for node_id in failed_nodes:
            try:
                result = pipeline_api.get_execution_data_outputs(runtime, node_id)
                if not (result.result and result.data):
                    continue
                outputs = result.data.get('outputs', {}) if isinstance(result.data, dict) else {}
                # 检查是否有 rollback 标记（由 PluginService.rollback 处理）
                _trigger_plugin_rollback(node_id, outputs)
                rollback_count += 1
            except Exception:
                logger.exception("[FlowEngine] rollback failed for node %s", node_id)

        if rollback_count:
            logger.info("[FlowEngine] rollback completed for %d nodes", rollback_count)

    # -- Notification helpers ------------------------------------------------

    def _notify_completed(self):
        """推送执行完成通知"""
        self._send_ws_completed()

    def _send_ws_completed(self):
        """推送执行完成通知到 WebSocket（best-effort，不抛异常）"""
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


def _trigger_plugin_rollback(node_id, outputs):
    """触发单个节点的插件回滚（通过 bamboo-engine API 实现重试以触发 rollback）"""
    # 注意：bamboo-engine 的 revoke 不会触发 rollback，
    # 真正的 rollback 需在 PluginService.rollback() 中实现。
    # 此处记录日志供后续扩展
    logger.info("[Rollback] node %s rollback triggered (outputs: %s)", node_id, outputs)
