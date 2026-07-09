# -*- coding: utf-8 -*-
"""ITSMEngine — ITSM Bamboo Pipeline 执行引擎

替代 PipelineWrapper，与 OpsFlow FlowEngine 保持一致的 instance 模式。
SLA 暂停/恢复由 ticket.set_status() 触发的信号自动处理（signals.py:ticket_post_save）。

用法:
    # 启动工单（实例方法，ticket 在构造时传入）
    engine = ITSMEngine(ticket)
    pipeline_id, tree = engine.run(workflow_version)

    # 暂停/恢复/撤销
    engine.pause()
    engine.resume()
    engine.revoke()

    # 回调（无 ticket 实例的静态方法）
    ITSMEngine.activity_callback(node_id, data)
"""

import logging

from bamboo_engine import api as pipeline_api
from pipeline.eri.runtime import BambooDjangoRuntime

from itsm.services.workflow_builder import ITSMWorkflowBuilder

logger = logging.getLogger(__name__)


class ITSMEngine:
    """ITSM 工单执行引擎 — BambooDjangoRuntime 驱动"""

    def __init__(self, ticket):
        self.ticket = ticket

    @property
    def _runtime(self):
        return BambooDjangoRuntime()

    # -- 实例化 API -----------------------------------------------------------

    def run(self, workflow_version):
        """创建并启动 pipeline（实例方法）

        Args:
            workflow_version: WorkflowVersion 实例（构建 pipeline tree）

        Returns:
            (pipeline_id, tree): pipeline ID + 完整 tree dict
        """
        ticket = self.ticket
        tree, _, node_id_map = ITSMWorkflowBuilder.build_tree(workflow_version, ticket.id)

        # Save node_id_map on ticket for callback resolution (_get_activity_id)
        # This ensures each pipeline run uses unique element IDs in the Data table
        meta = dict(ticket.meta or {})
        meta['_pipeline_id_map'] = node_id_map
        ticket.meta = meta
        ticket.save(update_fields=['meta'])
        logger.info(f'[ITSMEngine] saved _pipeline_id_map: {list(node_id_map.keys())[:5]}')

        pipeline_id = tree.get('id', '')
        runtime = BambooDjangoRuntime()
        result = pipeline_api.run_pipeline(runtime, tree)
        if not result.result:
            logger.error('[ITSMEngine] Pipeline run failed: %s', result.message)
            raise RuntimeError(f'Pipeline run failed: {result.message}')

        # 端到端 SLA 启动（pipeline 启动时只此一次）
        try:
            from itsm.services.sla_engine import SlaEngine
            SlaEngine.start_ticket_sla(self.ticket)
        except Exception as e:
            logger.warning('[ITSMEngine] SLA start failed: %s', e)

        return pipeline_id, tree

    def pause(self):
        """暂停 pipeline + SLA（由 ticket.set_status 信号自动处理）"""
        if self.ticket.pipeline_id:
            result = pipeline_api.pause_pipeline(self._runtime, self.ticket.pipeline_id)
            if not result.result:
                logger.error("[ITSMEngine] pause failed: %s", result.message)
        self.ticket.set_status('suspended')

    def resume(self):
        """恢复 pipeline + SLA（由 ticket.set_status 信号自动处理）"""
        if self.ticket.pipeline_id:
            result = pipeline_api.resume_pipeline(self._runtime, self.ticket.pipeline_id)
            if not result.result:
                logger.error("[ITSMEngine] resume failed: %s", result.message)
        self.ticket.set_status('running')

    def revoke(self):
        """撤销 pipeline + 停止 SLA（由 ticket.set_status 信号自动处理）"""
        if self.ticket.pipeline_id:
            result = pipeline_api.revoke_pipeline(self._runtime, self.ticket.pipeline_id)
            if not result.result:
                logger.error("[ITSMEngine] revoke failed: %s", result.message)
        self.ticket.set_status('terminated')

    @staticmethod
    def activity_callback(activity_id, callback_data):
        """向 bamboo-engine 发送节点回调（审批/填单操作完成）— delegate to shared."""
        from itsm.services.bamboo_engine import activity_callback as _cb
        return _cb(activity_id, callback_data)

    @staticmethod
    def revoke_by_pipeline_id(pipeline_id):
        """通过 pipeline_id 直接撤销 — delegate to shared."""
        from itsm.services.bamboo_engine import revoke_by_pipeline_id as _revoke
        return _revoke(pipeline_id)
