"""ServiceNow 查询事件 — 获取 ServiceNow 事件详情"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class ServicenowGetIncidentPlugin(BasePlugin):
    name = "ServiceNow 查询事件"
    name_en = "ServiceNow Get Incident"
    code = "servicenow_get_incident"
    version = "v1.0"
    icon = "InfoFilled"
    color = "#1890FF"
    group = "ServiceNow"
    description = "根据事件编号查询 ServiceNow 事件详情"
    description_en = "Get incident details from ServiceNow"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                name="ServiceNow 连接",
                name_en="ServiceNow Connection",
                tag_code="sn_connection",
                items=[
                    FormItem(
                        tag_code="instance_url",
                        type="async_select",
                        name="实例地址",
                        name_en="Instance URL",
                        attrs={
                            "api_endpoint": "/api/opsflow/cmdb/servicenow-instances/",
                            "value_key": "value",
                            "label_key": "label",
                            "searchable": True,
                            "placeholder": "从 CMDB 选择 ServiceNow 实例...",
                            "placeholder_en": "Select ServiceNow instance from CMDB...",
                        },
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="username",
                        type="input",
                        name="用户名",
                        name_en="Username",
                        attrs={"placeholder": "ServiceNow 用户名", "placeholder_en": "ServiceNow username"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="password",
                        type="input",
                        name="密码",
                        name_en="Password",
                        attrs={"placeholder": "密码或 API Token", "placeholder_en": "Password or API Token", "type": "password"},
                        validation=[ValidationRule(type="required")],
                    ),
                ],
            ),
            FormItem(
                tag_code="incident_number",
                type="input",
                name="事件编号",
                name_en="Incident Number",
                attrs={"placeholder": "INC0012345", "placeholder_en": "e.g. INC0012345"},
                validation=[ValidationRule(type="required")],
            ),
        ]

    def execute(self, instance_url: str, username: str, password: str,
                incident_number: str, **kwargs) -> dict:
        # 占位实现 — 集成实际 ServiceNow API 调用
        try:
            # TODO: 使用 requests 调用 ServiceNow REST API
            # resp = requests.get(
            #     f"{instance_url}/api/now/table/incident",
            #     params={"number": incident_number},
            #     headers={"Authorization": "Basic " + base64(...)},
            # )

            return {
                "success": True,
                "data": {
                    "instance_url": instance_url,
                    "incident_number": incident_number,
                    "short_description": "示例事件",
                    "state": "in_progress",
                    "category": "Network",
                    "urgency": "2",
                    "impact": "2",
                    "assigned_to": "john.doe",
                    "sys_id": "abc123def456",
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_url", "type": "string", "description": "实例地址", "description_en": "ServiceNow instance URL"},
            {"name": "incident_number", "type": "string", "description": "事件编号", "description_en": "Incident number"},
            {"name": "short_description", "type": "string", "description": "简要描述", "description_en": "Short description"},
            {"name": "state", "type": "string", "description": "状态", "description_en": "Current state"},
            {"name": "category", "type": "string", "description": "分类", "description_en": "Category"},
            {"name": "urgency", "type": "string", "description": "紧急度", "description_en": "Urgency"},
            {"name": "impact", "type": "string", "description": "影响范围", "description_en": "Impact"},
            {"name": "assigned_to", "type": "string", "description": "负责人", "description_en": "Assigned user"},
            {"name": "sys_id", "type": "string", "description": "系统 ID", "description_en": "ServiceNow sys_id"},
        ]
