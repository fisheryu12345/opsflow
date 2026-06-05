# -*- coding: utf-8 -*-
"""ITSM 工单审批通过后触发 OpsFlow 自愈流程

Ticket Opsflow Trigger — when a ticket completes approval,
auto-trigger an OpsFlow template execution based on TicketOpsflowConfig.
"""

import json
import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)

FSM = "opsflow_trigger"


class TicketOpsflowConfig(CoreModel):
    """ITSM 工单类型到 OpsFlow 模板的映射配置

    当指定类型的工单审批通过后，自动触发对应的 OpsFlow 模板执行，
    并将工单字段按 variable_mapping 映射为流程变量。
    """
    ticket_type = models.CharField(
        max_length=32,
        verbose_name="工单类型",
        help_text="与 Ticket.ITSM_TYPE_CHOICES 一致：change / incident / request / problem",
    )
    workflow = models.ForeignKey(
        'itsm.Workflow', on_delete=models.CASCADE, null=True, blank=True,
        related_name='opsflow_configs', verbose_name="关联 ITSM 流程",
        help_text="为空时对该类型所有工单生效",
    )
    opsflow_template = models.ForeignKey(
        'opsflow.FlowTemplate', on_delete=models.CASCADE,
        verbose_name="OpsFlow 模板",
        help_text="审批通过后触发的 OpsFlow 模板",
    )
    opsflow_scheme = models.ForeignKey(
        'opsflow.ExecutionScheme', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="执行方案",
        help_text="可选，指定执行方案（节点排除+变量覆盖）",
    )
    variable_mapping = models.JSONField(
        default=dict, verbose_name="字段映射",
        help_text="工单字段到 OpsFlow 全局变量的映射，如 {\"title\": \"${ticket_title}\"}",
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "itsm_opsflow_config"
        verbose_name = "ITSM-OpsFlow 触发配置"
        verbose_name_plural = verbose_name
        unique_together = [('ticket_type', 'workflow')]
        ordering = ['-create_datetime']

    def __str__(self):
        wf_name = self.workflow.name if self.workflow else "*"
        return f"[{self.ticket_type}] {wf_name} -> {self.opsflow_template.name}"


class OpsflowTriggerService:
    """ITSM 工单审批通过后触发 OpsFlow 自愈流程的服务"""

    FSM = "OpsflowTriggerService"

    @staticmethod
    def on_ticket_approved(ticket):
        """ITSM 工单审批通过回调 — 触发 OpsFlow 执行

        Args:
            ticket: Ticket 实例，需在调用前已保存

        Returns:
            dict: {triggered: bool, execution_id: int or None, message: str}
        """
        # 1. 查找匹配的触发配置
        config = OpsflowTriggerService._find_config(ticket)
        if not config:
            return {
                "triggered": False,
                "execution_id": None,
                "message": "未找到匹配的 OpsFlow 触发配置",
            }

        # 2. 解析变量映射
        resolved_vars = OpsflowTriggerService._resolve_variables(
            ticket, config.variable_mapping
        )

        # 3. 触发 OpsFlow 执行
        try:
            from opsflow.models import FlowExecution, FlowTemplate
            from opsflow.core.flow_engine import FlowEngine

            template = config.opsflow_template
            execution = FlowExecution.objects.create(
                template=template,
                created_by=ticket.creator,
                context={
                    "trigger": "itsm_ticket",
                    "ticket_id": ticket.id,
                    "ticket_sn": ticket.sn,
                    "ticket_title": ticket.title,
                    "params": resolved_vars,
                },
            )

            # 应用执行方案（节点排除+变量覆盖）
            if config.opsflow_scheme:
                scheme = config.opsflow_scheme
                if scheme.excluded_nodes:
                    execution.excluded_nodes = scheme.excluded_nodes

            execution.save(update_fields=["excluded_nodes"])

            engine = FlowEngine(execution)
            engine.start(sync=False)

            # 4. 将 execution_id 记录到 ticket.meta
            meta = dict(ticket.meta or {})
            meta["opsflow_execution_id"] = execution.id
            meta["opsflow_template_id"] = template.id
            meta["opsflow_template_name"] = template.name
            ticket.meta = meta
            ticket.save(update_fields=["meta"])

            logger.info(
                "[%s] Ticket %s (sn=%s) triggered OpsFlow execution %s",
                FSM, ticket.id, ticket.sn, execution.id,
            )

            return {
                "triggered": True,
                "execution_id": execution.id,
                "message": f"已触发 OpsFlow 执行 #{execution.id}",
            }

        except Exception as e:
            logger.exception(
                "[%s] Failed to trigger OpsFlow for ticket %s: %s",
                FSM, ticket.id, e,
            )
            return {
                "triggered": False,
                "execution_id": None,
                "message": f"触发失败: {str(e)}",
            }

    @staticmethod
    def _find_config(ticket):
        """查找与工单匹配的触发配置

        优先匹配 workflow + ticket_type，其次仅匹配 ticket_type。
        """
        # 优先精确匹配 workflow
        config = TicketOpsflowConfig.objects.filter(
            ticket_type=ticket.itsm_type,
            workflow=ticket.workflow_version.workflow,
            is_active=True,
        ).first()
        if config:
            return config

        # 回退到仅匹配 ticket_type
        config = TicketOpsflowConfig.objects.filter(
            ticket_type=ticket.itsm_type,
            workflow__isnull=True,
            is_active=True,
        ).first()
        return config

    @staticmethod
    def _resolve_variables(ticket, mapping: dict) -> dict:
        """按 variable_mapping 将工单字段解析为流程变量值

        Args:
            ticket: Ticket 实例
            mapping: dict, key=全局变量名, value=模板字符串

        Returns:
            dict: 解析后的变量字典
        """
        if not mapping:
            return {}

        # 构建工单字段上下文
        context = {
            "ticket_id": str(ticket.id),
            "ticket_sn": ticket.sn,
            "ticket_title": ticket.title,
            "ticket_type": ticket.itsm_type,
            "ticket_priority": ticket.priority,
            "ticket_creator": ticket.creator.username if ticket.creator else "",
            "ticket_status": ticket.current_status,
            "ticket_urgency": ticket.urgency,
            "ticket_impact": ticket.impact,
        }

        # 解析每个映射
        resolved = {}
        for var_name, template_str in mapping.items():
            try:
                # 简单模板替换 ${key} -> value
                value = template_str
                for key, val in context.items():
                    placeholder = "${" + key + "}"
                    if placeholder in value:
                        value = value.replace(placeholder, str(val))
                # 尝试 JSON 解析
                try:
                    resolved[var_name] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    resolved[var_name] = value
            except Exception as e:
                logger.warning(
                    "[%s] Failed to resolve variable %s: %s", FSM, var_name, e
                )
                resolved[var_name] = template_str

        return resolved
