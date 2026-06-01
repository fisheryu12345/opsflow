"""ServiceNow 创建变更 — 创建 ServiceNow 变更申请"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class ServicenowCreateChangeRequestPlugin(BasePlugin):
    name = "ServiceNow 创建变更"
    code = "servicenow_create_change_request"
    group = "ServiceNow"
    description = "在 ServiceNow 中创建变更申请 (Change Request)"
    risk_level = "medium"

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
                name="变更信息",
                tag_code="change_info",
                items=[
                    FormItem(
                        tag_code="short_description",
                        type="input",
                        name="简要描述",
                        attrs={"placeholder": "变更简要描述"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="description",
                        type="textarea",
                        name="详细描述",
                        attrs={"rows": 5, "placeholder": "变更详细描述（含实施计划）"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="category",
                        type="select",
                        name="变更类型",
                        default="Normal",
                        attrs={
                            "options": [
                                {"label": "标准 (Standard)", "value": "Standard"},
                                {"label": "正常 (Normal)", "value": "Normal"},
                                {"label": "紧急 (Emergency)", "value": "Emergency"},
                            ],
                        },
                    ),
                    FormItem(
                        tag_code="risk",
                        type="select",
                        name="风险等级",
                        default="3",
                        attrs={
                            "options": [
                                {"label": "1 - 极高", "value": "1"},
                                {"label": "2 - 高", "value": "2"},
                                {"label": "3 - 中", "value": "3"},
                                {"label": "4 - 低", "value": "4"},
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
                short_description: str, description: str, category: str = "Normal",
                risk: str = "3", assigned_to: str = "", **kwargs) -> dict:
        # 占位实现 — 集成实际 ServiceNow API 调用
        try:
            # TODO: 使用 requests 调用 ServiceNow REST API
            # headers = {"Authorization": "Basic " + base64(...), "Accept": "application/json"}
            # payload = {
            #     "short_description": short_description,
            #     "description": description,
            #     "category": category,
            #     "risk": risk,
            #     ...
            # }
            # resp = requests.post(f"{instance_url}/api/now/table/change_request", json=payload, headers=headers)

            return {
                "success": True,
                "data": {
                    "instance_url": instance_url,
                    "change_number": "CHG0012345",
                    "short_description": short_description,
                    "category": category,
                    "risk": risk,
                    "state": "new",
                    "sys_id": "chg789abc012",
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}
