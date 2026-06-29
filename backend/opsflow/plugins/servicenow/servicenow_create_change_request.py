"""ServiceNow 创建变更 — 创建 ServiceNow 变更申请"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class ServicenowCreateChangeRequestPlugin(BasePlugin):
    name = "ServiceNow 创建变更"
    name_en = "ServiceNow Create Change Request"
    code = "servicenow_create_change_request"
    version = "v1.0"
    icon = "Edit"
    color = "#1890FF"
    group = "ServiceNow"
    description = "在 ServiceNow 中创建变更申请 (Change Request)"
    description_en = "Create a change request in ServiceNow"
    risk_level = "medium"

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
            FormGroup(
                name="变更信息",
                name_en="Change Information",
                tag_code="change_info",
                items=[
                    FormItem(
                        tag_code="short_description",
                        type="input",
                        name="简要描述",
                        name_en="Short Description",
                        attrs={"placeholder": "变更简要描述", "placeholder_en": "Brief change description"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="description",
                        type="textarea",
                        name="详细描述",
                        name_en="Detailed Description",
                        attrs={"rows": 5, "placeholder": "变更详细描述（含实施计划）", "placeholder_en": "Detailed change description with implementation plan"},
                        validation=[ValidationRule(type="required")],
                    ),
                    FormItem(
                        tag_code="category",
                        type="select",
                        name="变更类型",
                        name_en="Category",
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
                        name_en="Risk Level",
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
                        name_en="Assigned To",
                        attrs={"placeholder": "负责人用户名（可选）", "placeholder_en": "Assignee username (optional)"},
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

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_url", "type": "string", "description": "实例地址", "description_en": "ServiceNow instance URL"},
            {"name": "change_number", "type": "string", "description": "变更编号", "description_en": "Change request number"},
            {"name": "short_description", "type": "string", "description": "简要描述", "description_en": "Short description"},
            {"name": "category", "type": "string", "description": "变更类型", "description_en": "Change category"},
            {"name": "risk", "type": "string", "description": "风险等级", "description_en": "Risk level"},
            {"name": "state", "type": "string", "description": "状态", "description_en": "Current state"},
            {"name": "sys_id", "type": "string", "description": "系统 ID", "description_en": "ServiceNow sys_id"},
        ]
