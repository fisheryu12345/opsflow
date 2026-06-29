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
    name_en = "Create ITSM Ticket"
    code = "itsm_create_ticket"
    group = "ITSM"
    description = "在 OpsFlow 执行节点中创建 ITSM 工单，支持指定流程模板并自动填充字段"
    description_en = "Create a new ITSM service ticket"
    risk_level = "low"
    version = "v1.0"
    icon = "Document"
    color = "#409EFF"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="itsm_type",
                type="select",
                name="工单类型",
                name_en="Ticket Type",
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
                name_en="Workflow Template",
                scope="global",
                attrs={
                    "placeholder": "选择 ITSM 流程模板",
                    "placeholder_en": "Select ITSM workflow template",
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
                name_en="Ticket Title",
                scope="global",
                attrs={"placeholder": "工单标题，支持 ${var} 模板变量", "placeholder_en": "Ticket title, supports ${var} template variables"},
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="priority",
                type="select",
                name="优先级",
                name_en="Priority",
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
                name_en="Ticket Description",
                scope="global",
                attrs={
                    "rows": 4,
                    "placeholder": "工单描述，支持 ${var} 模板变量",
                    "placeholder_en": "Ticket description, supports ${var} template variables",
                },
            ),
            FormItem(
                tag_code="fields_data",
                type="textarea",
                name="额外字段",
                name_en="Extra Fields",
                scope="global",
                attrs={
                    "rows": 3,
                    "placeholder": 'JSON 格式，如 {"field_key": "value"}，支持 ${var} 模板变量',
                    "placeholder_en": 'JSON format, e.g. {"field_key": "value"}, supports ${var} template variables',
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

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "ticket_id", "type": "int", "description": "工单 ID", "description_en": "Ticket ID"},
            {"name": "sn", "type": "string", "description": "工单编号", "description_en": "Ticket serial number"},
            {"name": "title", "type": "string", "description": "工单标题", "description_en": "Ticket title"},
            {"name": "status", "type": "string", "description": "工单状态", "description_en": "Ticket status"},
            {"name": "workflow", "type": "string", "description": "流程模板名称", "description_en": "Workflow template name"},
        ]

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
