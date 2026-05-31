"""ServiceNow 更新事件 — 更新 ServiceNow 事件记录"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class ServicenowUpdateIncidentPlugin(BasePlugin):
    name = "ServiceNow 更新事件"
    code = "servicenow_update_incident"
    group = "ServiceNow"
    description = "更新 ServiceNow 事件 (Incident) 的状态或字段"
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
            FormItem(
                tag_code="state",
                type="select",
                name="状态",
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
                attrs={"rows": 4, "placeholder": "处理备注"},
            ),
            FormItem(
                tag_code="close_code",
                type="select",
                name="关闭代码",
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
