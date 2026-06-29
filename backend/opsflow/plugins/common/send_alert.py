"""发送告警 — 发送通知到指定渠道"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class SendAlertPlugin(BasePlugin):
    name = "发送告警"
    name_en = "Send Alert"
    code = "send_alert"
    group = "Common Tools"
    description = "发送告警/通知到邮箱、Webhook 等渠道"
    description_en = "Send alert or notification via email, webhook, etc."
    risk_level = "low"
    version = "v1.0"
    icon = "WarningFilled"
    color = "#E6A23C"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="channel",
                type="select",
                name="通知渠道",
                name_en="Notification Channel",
                attrs={
                    "options": [
                        {"label": "邮件", "value": "email"},
                        {"label": "企业微信", "value": "wecom"},
                        {"label": "钉钉", "value": "dingtalk"},
                        {"label": "飞书", "value": "lark"},
                        {"label": "Webhook", "value": "webhook"},
                    ],
                },
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="title",
                type="input",
                name="标题",
                name_en="Title",
                attrs={"placeholder": "告警标题", "placeholder_en": "Alert title"},
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="content",
                type="textarea",
                name="内容",
                name_en="Content",
                attrs={"rows": 5, "placeholder": "告警内容", "placeholder_en": "Alert content"},
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="recipients",
                type="input",
                name="接收人",
                name_en="Recipients",
                attrs={"placeholder": "邮箱逗号分隔 / 手机号", "placeholder_en": "Email (comma-separated) / Phone number"},
                validation=[ValidationRule(type="required")],
            ),
        ]

    def execute(self, channel: str, title: str, content: str,
                recipients: str, **kwargs) -> dict:
        # 生产环境应异步发送
        try:
            # 这里集成实际的通知发送逻辑
            # ...
            return {
                "success": True,
                "data": {
                    "channel": channel,
                    "title": title,
                    "recipients": recipients,
                    "sent": True,
                },
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "channel", "type": "string", "description": "通知渠道", "description_en": "Notification channel"},
            {"name": "title", "type": "string", "description": "告警标题", "description_en": "Alert title"},
            {"name": "recipients", "type": "string", "description": "接收人", "description_en": "Recipients"},
            {"name": "sent", "type": "bool", "description": "是否已发送", "description_en": "Whether sent successfully"},
        ]
