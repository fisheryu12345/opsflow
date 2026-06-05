"""Create ITSM Ticket — 在 OpsFlow 执行节点中创建 ITSM 工单

在自愈流程中，当需要人工介入时调用此插件创建 ITSM 工单，
将上下文变量自动填充到工单字段中。
"""

import logging

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule

logger = logging.getLogger(__name__)

FSM = "itsm_create_ticket"


class CreateItsmTicketPlugin(BasePlugin):
    name = "创建 ITSM 工单"
    code = "itsm_create_ticket"
    group = "ITSM"
    description = "在 OpsFlow 执行节点中创建 ITSM 工单，支持指定流程模板并自动填充字段"
    risk_level = "low"
    icon = "Document"
    color = "#409EFF"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="itsm_type",
                type="select",
                name="工单类型",
                attrs={
                    "options": [
                        {"label": "变更申请", "value": "change"},
                        {"label": "事件工单", "value": "incident"},
                        {"label": "服务请求", "value": "request"},
                        {"label": "问题管理", "value": "problem"},
                    ],
                },
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="workflow_id",
                type="select",
                name="流程模板",
                scope="global",
                attrs={
                    "placeholder": "选择 ITSM 流程模板",
                    "options": [],
                    "remote_url": "/api/itsm/workflows/?is_draft=false&is_enabled=true",
                    "remote_label": "name",
                    "remote_value": "id",
                },
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="title",
                type="input",
                name="工单标题",
                scope="global",
                attrs={"placeholder": "工单标题，支持 ${var} 模板变量"},
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="priority",
                type="select",
                name="优先级",
                default="P3",
                attrs={
                    "options": [
                        {"label": "P1 危急", "value": "P1"},
                        {"label": "P2 高", "value": "P2"},
                        {"label": "P3 中", "value": "P3"},
                        {"label": "P4 低", "value": "P4"},
                    ],
                },
            ),
            FormItem(
                tag_code="description",
                type="textarea",
                name="工单描述",
                scope="global",
                attrs={
                    "rows": 4,
                    "placeholder": "工单描述，支持 ${var} 模板变量",
                },
            ),
            FormItem(
                tag_code="fields_data",
                type="textarea",
                name="额外字段",
                scope="global",
                attrs={
                    "rows": 3,
                    "placeholder": 'JSON 格式，如 {"field_key": "value"}，支持 ${var} 模板变量',
                },
            ),
        ]

    @classmethod
    def get_var_types(cls) -> dict:
        return {
            "title": "splice",
            "description": "splice",
            "fields_data": "splice",
        }

    def execute(self, itsm_type: str, title: str,
                workflow_id: int = None, priority: str = "P3",
                description: str = "", fields_data: str = "",
                **kwargs) -> dict:
        try:
            from itsm.models import Ticket, WorkflowVersion, Workflow

            # 查找流程版本
            if workflow_id:
                workflow = Workflow.objects.get(id=workflow_id, is_enabled=True)
                workflow_version = workflow.versions.first()
                if not workflow_version:
                    # 自动部署
                    workflow_version = workflow.create_version(
                        operator="opsflow",
                        message="OpsFlow 自动部署",
                    )
            else:
                # 按工单类型查找默认流程
                workflow = Workflow.objects.filter(
                    itsm_type=itsm_type, is_enabled=True
                ).first()
                if not workflow:
                    return {
                        "success": False,
                        "data": {},
                        "error": f"未找到启用的 {itsm_type} 流程模板",
                    }
                workflow_version = workflow.versions.first()
                if not workflow_version:
                    workflow_version = workflow.create_version(
                        operator="opsflow",
                        message="OpsFlow 自动部署",
                    )

            # 解析额外字段
            extra_fields = {}
            if fields_data:
                import json
                try:
                    extra_fields = json.loads(fields_data)
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "data": {},
                        "error": f"fields_data 不是有效的 JSON: {e}",
                    }

            # 创建工单
            ticket = Ticket.objects.create(
                title=title,
                itsm_type=itsm_type,
                priority=priority,
                workflow_version=workflow_version,
                meta={
                    "source": "opsflow",
                    "description": description,
                    **extra_fields,
                },
            )

            # 初始化工单
            ticket.do_after_create()

            logger.info(
                "[%s] Created ITSM ticket %s (sn=%s) from OpsFlow execution",
                FSM, ticket.id, ticket.sn,
            )

            return {
                "success": True,
                "data": {
                    "ticket_id": ticket.id,
                    "sn": ticket.sn,
                    "title": ticket.title,
                    "status": ticket.current_status,
                    "workflow": workflow.name,
                },
            }

        except Exception as e:
            logger.exception("[%s] Failed to create ITSM ticket: %s", FSM, e)
            return {"success": False, "data": {}, "error": str(e)}
