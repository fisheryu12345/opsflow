"""Flow Execution Engine — BambooDjangoRuntime + bamboo_engine.api

所有执行通过 bamboo-engine 异步驱动（Celery + 信号），与 bk-sops 一致。
节点状态追踪通过 post_set_state 信号异步完成（见 signals.py）。
"""

import datetime
import logging

from bamboo_engine import api as pipeline_api
from bamboo_engine.builder import Data, Var
from bamboo_engine.exceptions import ConnectionValidateError
from pipeline.eri.runtime import BambooDjangoRuntime

from opsflow.core.pipeline_builder import build_bamboo_pipeline
from opsflow.core.safety_guard import validate_pipeline

logger = logging.getLogger(__name__)


class FlowEngine:
    """流程执行引擎 — BambooDjangoRuntime 驱动（仅异步路径）"""

    def __init__(self, execution):
        self.execution = execution
        self.template = execution.template

    @property
    def _runtime(self):
        return BambooDjangoRuntime()

    def _update_node_status(self, node_id, status="retrying"):
        """更新节点状态和执行状态（retry/retry_subprocess 共享）"""
        node_status = self.execution.node_status or {}
        node_status[node_id] = status
        self.execution.node_status = node_status
        self.execution.status = "running"
        self.execution.save(update_fields=["node_status", "status"])

    def _fail_execution(self, msg, save_fields=None, do_rollback=False):
        """标记执行为失败状态 — run() 中多处失败路径共享"""
        self.execution.status = "failed"
        self.execution.ended_at = datetime.datetime.now()
        if msg:
            self.execution.context['_validation_error'] = msg
        save_fields = save_fields or ["status", "ended_at"]
        if msg:
            save_fields.append("context")
        self.execution.save(update_fields=save_fields)
        if do_rollback:
            self.rollback_failed_nodes()
        self._notify_completed()

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
            result = pipeline_api.pause_pipeline(self._runtime, bamboo_pipeline_id)
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
        result = pipeline_api.resume_pipeline(self._runtime, bamboo_pipeline_id)
        if not result.result:
            logger.error("[FlowEngine] resume failed: %s", result.message)
            return
        self.execution.status = "running"
        self.execution.save(update_fields=["status"])

    def retry(self, node_id):
        """重试指定失败节点 — 委托给 BambooDjangoRuntime"""
        result = pipeline_api.retry_node(self._runtime, node_id)
        if not result.result:
            logger.error("[FlowEngine] retry node %s failed: %s", node_id, result.message)
        else:
            self._update_node_status(node_id, "retrying")

    def retry_subprocess(self, node_id):
        """重试子流程节点 — 委托给 bamboo_engine.api.retry_subprocess"""
        result = pipeline_api.retry_subprocess(self._runtime, node_id)
        if not result.result:
            logger.error("[FlowEngine] retry subprocess %s failed: %s", node_id, result.message)
        else:
            self._update_node_status(node_id, "retrying")

    def skip(self, node_id):
        """跳过指定失败节点 — 委托给 BambooDjangoRuntime"""
        result = pipeline_api.skip_node(self._runtime, node_id)
        if not result.result:
            logger.error("[FlowEngine] skip node %s failed: %s", node_id, result.message)
        else:
            node_status = self.execution.node_status or {}
            node_status[node_id] = "skipped"
            self.execution.node_status = node_status
            self.execution.save(update_fields=["node_status"])

    def force_fail(self, node_id, ex_data=""):
        """强制让指定节点进入失败状态 — 委托给 BambooDjangoRuntime"""
        result = pipeline_api.forced_fail_activity(
            self._runtime, node_id, ex_data=ex_data, send_post_set_state_signal=True,
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
            result = pipeline_api.revoke_pipeline(self._runtime, bamboo_pipeline_id)
            if not result.result:
                logger.error("[FlowEngine] cancel failed: %s", result.message)
        self.execution.status = "cancelled"
        self.execution.ended_at = datetime.datetime.now()
        self.execution.save(update_fields=["status", "ended_at"])
        self._send_ws_completed()
        logger.info("[FlowEngine] execution %s cancelled", self.execution.id)

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
                    self._fail_execution(errors)
                    return
            pipeline, _ = build_bamboo_pipeline(
                self.template,
                pipeline_tree=frozen_tree,
                target_hosts=frozen.get('target_hosts'),
                global_vars=frozen.get('global_vars'),
                execution_id=self.execution.id,
                excluded_nodes=self.execution.excluded_nodes,
            )
            # DEBUG: 打印 pipeline 拓扑结构
            acts = pipeline.get('activities', {})
            gws = pipeline.get('gateways', {})
            flows = pipeline.get('flows', {})
            logger.info("[FlowEngine] Pipeline tree built: %d activities, %d gateways, %d flows",
                        len(acts), len(gws), len(flows))
            for _aid, _act in acts.items():
                logger.info("  activity %s: type=%s, outgoing=%s",
                            _aid, _act.get('type'), _act.get('outgoing'))
            for _gid, _gw in gws.items():
                logger.info("  gateway %s: type=%s, outgoing=%s",
                            _gid, _gw.get('type'), _gw.get('outgoing'))

            # 空 pipeline 检测：没有活动节点也没有网关 → 模板未保存节点或 pipeline_tree 为空
            if len(acts) == 0 and len(gws) == 0:
                msg = "pipeline 为空：模板中没有节点或节点已被全部过滤，请检查模板并先保存后再执行"
                logger.error("[FlowEngine] " + msg)
                self._fail_execution(msg, save_fields=["status", "ended_at", "context"])
                return

            bamboo_pipeline_id = pipeline.get("id", "")

            # 执行前创建自动重试策略和超时配置（参考 bk_sops）
            try:
                from opsflow.core.auto_retry import AutoRetryStrategyCreator
                creator = AutoRetryStrategyCreator(self.execution, bamboo_pipeline_id)
                creator.batch_create_strategy(frozen_tree or {})
            except Exception as e:
                logger.warning("[FlowEngine] batch_create_strategy error: %s", e)

            try:
                from opsflow.core.node_timeout_strategy import batch_create_timeout_configs
                batch_create_timeout_configs(self.execution, frozen_tree or {})
            except Exception as e:
                logger.warning("[FlowEngine] batch_create_timeout_configs error: %s", e)

            self.execution.context["bamboo_pipeline_id"] = bamboo_pipeline_id
            self.execution.context["bamboo_pipeline"] = pipeline
            self.execution.save(update_fields=["context"])

            # 清理重试时可能残留的 pipeline data（Data/State/ExecutionData 的 node_id 唯一约束）
            try:
                self._cleanup_pipeline_data(pipeline)
            except Exception as e:
                logger.warning("[FlowEngine] _cleanup_pipeline_data error: %s", e)

            result = pipeline_api.run_pipeline(runtime=self._runtime, pipeline=pipeline)

            if not result.result:
                # 提取验证错误详情（ConnectionValidateError 含 failed_nodes + detail）
                if hasattr(result, 'exc') and isinstance(result.exc, ConnectionValidateError):
                    exc = result.exc
                    detail_msg = "; ".join(
                        f"Node {nid}: {str(detail).strip()}" for nid, detail in exc.detail.items()
                    )
                    logger.error("[FlowEngine] run_pipeline failed (validation errors): %s | failed_nodes=%s",
                                 detail_msg, exc.failed_nodes)
                    self.execution.context['_validation_error'] = detail_msg
                else:
                    logger.error("[FlowEngine] run_pipeline failed: %s", result.message)
                    self.execution.context['_validation_error'] = result.message
                self._fail_execution(self.execution.context.get('_validation_error'),
                                     save_fields=["status", "ended_at", "context"],
                                     do_rollback=True)
                return

            logger.info(
                "[FlowEngine] pipeline %s dispatched (async execution via er_execute queue)",
                bamboo_pipeline_id,
            )

        except Exception as e:
            logger.exception("[FlowEngine] run failed")
            if '_validation_error' not in self.execution.context:
                self.execution.context['_validation_error'] = str(e)
            self._fail_execution(self.execution.context.get('_validation_error'),
                                 save_fields=["status", "ended_at", "context"],
                                 do_rollback=True)

    # -- Rollback / Compensation -------------------------------------------

    def rollback_failed_nodes(self):
        """Pipeline 失败后，遍历所有失败节点并调用其 rollback 方法"""
        node_status = self.execution.node_status or {}
        failed_nodes = [nid for nid, st in node_status.items() if st in ('failed',)]
        if not failed_nodes:
            return

        logger.info("[FlowEngine] rolling back %d failed nodes", len(failed_nodes))
        rollback_count = 0
        for node_id in failed_nodes:
            try:
                result = pipeline_api.get_execution_data_outputs(self._runtime, node_id)
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

    # -- Pipeline Re-run Cleanup --------------------------------------------

    def _cleanup_pipeline_data(self, pipeline: dict):
        """清理重试执行时残留的 bamboo-engine pipeline 数据

        退出重试场景：pipeline 已存在旧的 Data/State/ExecutionData 记录，
        其 node_id 使用模板原始 ID（如 node_1、node_3），再次运行会因
        唯一约束冲突而失败。该方法在调用 run_pipeline 之前清理所有
        与本次 pipeline 节点 ID 关联的旧记录。
        """
        all_node_ids = set()
        for act_id in pipeline.get('activities', {}):
            all_node_ids.add(act_id)
        for gw_id in pipeline.get('gateways', {}):
            all_node_ids.add(gw_id)
        start = pipeline.get('start_event', {})
        if start:
            all_node_ids.add(start.get('id'))
        end = pipeline.get('end_event', {})
        if end:
            all_node_ids.add(end.get('id'))
        all_node_ids.discard(None)

        if not all_node_ids:
            return

        from pipeline.eri.models import Data as PipelineData, State as PipelineState
        from pipeline.eri.models import ExecutionData as PipelineExecutionData
        from pipeline.eri.models import Schedule as PipelineSchedule
        from pipeline.eri.models import Node as PipelineNode
        from pipeline.eri.models import ExecutionHistory as PipelineExecutionHistory
        from pipeline.eri.models import CallbackData as PipelineCallbackData

        logger.info("[FlowEngine] Cleaning pipeline data for %d node IDs (re-run cleanup)",
                     len(all_node_ids))
        PipelineData.objects.filter(node_id__in=all_node_ids).delete()
        PipelineExecutionData.objects.filter(node_id__in=all_node_ids).delete()
        PipelineState.objects.filter(node_id__in=all_node_ids).delete()
        PipelineSchedule.objects.filter(node_id__in=all_node_ids).delete()
        PipelineNode.objects.filter(node_id__in=all_node_ids).delete()
        PipelineExecutionHistory.objects.filter(node_id__in=all_node_ids).delete()
        PipelineCallbackData.objects.filter(node_id__in=all_node_ids).delete()

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
