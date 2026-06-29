"""审批原子 — Pipeline 执行到此处时暂停，等待指定审批人审批"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class ApprovalPlugin(BasePlugin):
    name = "审批"
    name_en = "Approval"
    code = "approval"
    group = "流程控制"
    description = "暂停流程并等待指定审批人审批"
    description_en = "Pause pipeline and wait for specified approvers"
    risk_level = "low"
    icon = "Clock"
    color = "#9B59B6"

    show_execution_controls = False
    show_loop_config = False

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="approvers",
                type="async_select",
                name="审批人",
                name_en="Approvers",
                attrs={
                    "api_endpoint": "/api/iam/users/search/",
                    "multiple": True,
                    "searchable": True,
                    "placeholder": "搜索并选择审批人",
                },
                validation=[ValidationRule(type="required")],
            ),
        ]

    def execute(self, approvers=None, **kwargs):
        """校验参数并返回成功，暂停由 PluginService 处理"""
        if not approvers:
            return {"success": False, "error": "请选择审批人"}
        return {"success": True, "data": {"approvers": approvers}}
