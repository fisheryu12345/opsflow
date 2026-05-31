"""ServiceNow 查询事件 — 获取 ServiceNow 事件详情"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class ServicenowGetIncidentPlugin(BasePlugin):
    name = "ServiceNow 查询事件"
    code = "servicenow_get_incident"
    group = "ServiceNow"
    description = "根据事件编号查询 ServiceNow 事件详情"
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
                        type="input",
                        name="实例地址",
                        attrs={"placeholder": "https://your-instance.service-now.com"},
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
            FormItem(
                tag_code="incident_number",
                type="input",
                name="事件编号",
                attrs={"placeholder": "INC0012345"},
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
