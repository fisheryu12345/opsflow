"""ServiceNow 更新事件 — 更新 ServiceNow 事件记录"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class ServicenowUpdateIncidentPlugin(BasePlugin):
    name = "ServiceNow 更新事件"
    name_en = "ServiceNow Update Incident"
    code = "servicenow_update_incident"
    version = "v1.0"
    icon = "EditPen"
    color = "#1890FF"
    group = "ServiceNow"
    description = "更新 ServiceNow 事件 (Incident) 的状态或字段"
    description_en = "Update an incident in ServiceNow"
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
            FormItem(
                tag_code="state",
                type="select",
                name="状态",
                name_en="State",
                default="2",
                attrs={
                    "options": [
                        {"label": "新建 (New)", "value": "1"},
                        {"label": "处理中 (In Progress)", "value": "2"},
                        {"label": "已解决 (Resolved)", "value": "3"},
                        {"label": "已关闭 (Closed)", "value": "7"},
                    ],
                },
            ),
            FormItem(
                tag_code="work_notes",
                type="textarea",
                name="工作备注",
                name_en="Work Notes",
                attrs={"rows": 4, "placeholder": "处理备注", "placeholder_en": "Work notes"},
            ),
            FormItem(
                tag_code="close_code",
                type="select",
                name="关闭代码",
                name_en="Close Code",
                default="",
                attrs={
                    "options": [
                        {"label": "（不关闭）", "value": ""},
                        {"label": "已修复 (Fixed)", "value": "Fixed"},
                        {"label": "已解决 (Solved)", "value": "Solved"},
                        {"label": "无法重现 (Unable to Reproduce)", "value": "Unable to Reproduce"},
                        {"label": "重复 (Duplicate)", "value": "Duplicate"},
                    ],
                },
            ),
        ]

    def execute(self, instance_url: str, username: str, password: str,
                incident_number: str, state: str = "2", work_notes: str = "",
                close_code: str = "", **kwargs) -> dict:
        # 占位实现 — 集成实际 ServiceNow API 调用
        try:
            # TODO: 使用 requests 调用 ServiceNow REST API
            # payload = {"state": state}
            # if work_notes:
            #     payload["work_notes"] = work_notes
            # if close_code:
            #     payload["close_code"] = close_code
            # resp = requests.patch(f"{instance_url}/api/now/table/incident/{sys_id}", json=payload, ...)

            return {
                "success": True,
                "data": {
                    "instance_url": instance_url,
                    "incident_number": incident_number,
                    "state": state,
                    "work_notes_added": bool(work_notes),
                    "close_code": close_code,
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_url", "type": "string", "description": "实例地址", "description_en": "ServiceNow instance URL"},
            {"name": "incident_number", "type": "string", "description": "事件编号", "description_en": "Incident number"},
            {"name": "state", "type": "string", "description": "状态", "description_en": "Updated state"},
            {"name": "work_notes_added", "type": "bool", "description": "是否添加备注", "description_en": "Whether work notes were added"},
            {"name": "close_code", "type": "string", "description": "关闭代码", "description_en": "Close code"},
        ]
