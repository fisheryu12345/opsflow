# -*- coding: utf-8 -*-
"""ITSMEngine — ITSM Bamboo Pipeline 执行引擎

替代 PipelineWrapper，与 OpsFlow FlowEngine 保持一致的 instance 模式。
SLA 暂停/恢复由 ticket.set_status() 触发的信号自动处理（signals.py:ticket_post_save）。

用法:
    # 启动工单
    ITSMEngine.run(ticket, workflow_version)

    # 暂停/恢复/撤销（基于工单实例）
    engine = ITSMEngine(ticket)
    engine.pause()
    engine.resume()
    engine.revoke()

    # 回调
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

    # -- 静态 API -------------------------------------------------------------

    @staticmethod
    def run(ticket, workflow_version):
        """创建并启动 pipeline

        Args:
            ticket: Ticket 实例
            workflow_version: WorkflowVersion 实例（构建 pipeline tree）

        Returns:
            (pipeline_id, tree): pipeline ID + 完整 tree dict
        """
        tree, _ = ITSMWorkflowBuilder.build_tree(workflow_version, ticket.id)
        pipeline_id = tree.get('id', '')
        runtime = BambooDjangoRuntime()
        result = pipeline_api.run_pipeline(runtime, tree)
        if not result.result:
            logger.error('[ITSMEngine] Pipeline run failed: %s', result.message)
            raise RuntimeError(f'Pipeline run failed: {result.message}')
        return pipeline_id, tree

    @staticmethod
    def activity_callback(activity_id, callback_data):
        """向 bamboo-engine 发送节点回调（审批/填单操作完成）"""
        runtime = BambooDjangoRuntime()
        result = pipeline_api.activity_callback(runtime, activity_id, callback_data)
        if not result.result:
            logger.error('[ITSMEngine] activity_callback failed: %s', result.message)
        return result.result

    @staticmethod
    def revoke_by_pipeline_id(pipeline_id):
        """通过 pipeline_id 直接撤销（供 opsflow 插件等无 ticket 实例的场景调用）

        仅撤销 pipeline，不操作工单状态（由调用方自行处理）。
        """
        runtime = BambooDjangoRuntime()
        result = pipeline_api.revoke_pipeline(runtime, pipeline_id)
        if not result.result:
            logger.error('[ITSMEngine] revoke_by_pipeline_id failed: %s', result.message)
        return result.result
