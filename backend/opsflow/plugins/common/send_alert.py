"""发送告警 — 发送通知到指定渠道"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class SendAlertPlugin(BasePlugin):
    name = "发送告警"
    code = "send_alert"
    group = "通用工具"
    description = "发送告警/通知到邮箱、Webhook 等渠道"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="channel",
                type="select",
                name="通知渠道",
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
                attrs={"placeholder": "告警标题"},
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="content",
                type="textarea",
                name="内容",
                attrs={"rows": 5, "placeholder": "告警内容"},
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="recipients",
                type="input",
                name="接收人",
                attrs={"placeholder": "邮箱逗号分隔 / 手机号"},
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
