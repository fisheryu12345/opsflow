"""ServiceNow 创建事件 — 创建 ServiceNow 事件记录"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class ServicenowCreateIncidentPlugin(BasePlugin):
    name = "ServiceNow 创建事件"
    code = "servicenow_create_incident"
    group = "ServiceNow"
    description = "在 ServiceNow 中创建事件 (Incident) 记录"
    description_en = "Create an incident in ServiceNow"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                name="ServiceNow 连接",
                tag_code="sn_connection",
                items=[
                    FormItem(
                        tag_code="instance_url",
                        type="async_select",
                        name="实例地址",
                        attrs={
                            "api_endpoint": "/api/opsflow/cmdb/servicenow-instances/",
                            "value_key": "value",
                            "label_key": "label",
                            "searchable": True,
                            "placeholder": "从 CMDB 选择 ServiceNow 实例...",
                        },
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="username",
                        type="input",
                        name="用户名",
                        attrs={"placeholder": "ServiceNow 用户名"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="password",
                        type="input",
                        name="密码",
                        attrs={"placeholder": "密码或 API Token", "type": "password"},
                        validation=[ValidationRule(type="required")],
                    ),
                ],
            ),
            FormGroup(
                name="事件信息",
                tag_code="incident_info",
                items=[
                    FormItem(
                        tag_code="short_description",
                        type="input",
                        name="简要描述",
                        attrs={"placeholder": "事件简要描述"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="description",
                        type="textarea",
                        name="详细描述",
                        attrs={"rows": 5, "placeholder": "事件详细描述"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="category",
                        type="select",
                        name="分类",
                        default="Network",
                        attrs={
                            "options": [
                                {"label": "网络 (Network)", "value": "Network"},
                                {"label": "软件 (Software)", "value": "Software"},
                                {"label": "硬件 (Hardware)", "value": "Hardware"},
                                {"label": "数据库 (Database)", "value": "Database"},
                                {"label": "安全 (Security)", "value": "Security"},
                            ],
                        },
                    ),
                    FormItem(
                        tag_code="urgency",
                        type="select",
                        name="紧急度",
                        default="3",
                        attrs={
                            "options": [
                                {"label": "1 - 高", "value": "1"},
                                {"label": "2 - 中", "value": "2"},
                                {"label": "3 - 低", "value": "3"},
                            ],
                        },
                    ),
                    FormItem(
                        tag_code="impact",
                        type="select",
                        name="影响范围",
                        default="3",
                        attrs={
                            "options": [
                                {"label": "1 - 大范围", "value": "1"},
                                {"label": "2 - 中等", "value": "2"},
                                {"label": "3 - 局部", "value": "3"},
                            ],
                        },
                    ),
                    FormItem(
                        tag_code="assigned_to",
                        type="input",
                        name="指派给",
                        attrs={"placeholder": "负责人用户名（可选）"},
                    ),
                ],
            ),
        ]

    def execute(self, instance_url: str, username: str, password: str,
                short_description: str, description: str, category: str = "Network",
                urgency: str = "3", impact: str = "3", assigned_to: str = "",
                **kwargs) -> dict:
        # 占位实现 — 集成实际 ServiceNow API 调用
        try:
            # TODO: 使用 requests 调用 ServiceNow REST API
            # headers = {"Authorization": "Basic " + base64(...), "Accept": "application/json"}
            # payload = {
            #     "short_description": short_description,
            #     "description": description,
            #     "category": category,
            #     "urgency": urgency,
            #     "impact": impact,
            #     ...
            # }
            # resp = requests.post(f"{instance_url}/api/now/table/incident", json=payload, headers=headers)

            return {
                "success": True,
                "data": {
                    "instance_url": instance_url,
                    "incident_number": "INC0012345",
                    "short_description": short_description,
                    "category": category,
                    "urgency": urgency,
                    "impact": impact,
                    "state": "new",
                    "sys_id": "abc123def456",
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}
