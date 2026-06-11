"""发送邮件 — 通过 SMTP 发送电子邮件通知"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class SendEmailPlugin(BasePlugin):
    name = "发送邮件"
    name_en = "Send Email"
    code = "send_email"
    group = "通用工具"
    description = "通过 SMTP 邮件服务器发送电子邮件通知"
    description_en = "Send email notifications via SMTP server"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="smtp_host",
                type="input",
                name="SMTP 服务器",
                name_en="SMTP Server",
                attrs={"placeholder": "smtp.example.com"},
                validation=[ValidationRule(type="required")],
                col=8,
            ),
            FormItem(
                tag_code="smtp_port",
                type="int",
                name="端口",
                name_en="Port",
                default=465,
                attrs={"min": 1, "max": 65535},
                col=4,
            ),
            FormItem(
                tag_code="smtp_user",
                type="input",
                name="用户名",
                name_en="Username",
                attrs={"placeholder": "user@example.com"},
                validation=[ValidationRule(type="required")],
                col=6,
            ),
            FormItem(
                tag_code="smtp_password",
                type="input",
                name="密码/授权码",
                name_en="Password",
                attrs={"type": "password", "placeholder": "SMTP 密码或授权码"},
                validation=[ValidationRule(type="required")],
                col=6,
            ),
            FormItem(
                tag_code="use_tls",
                type="switch",
                name="TLS 加密",
                name_en="TLS Encryption",
                default=True,
                attrs={"active_text": "开启", "inactive_text": "关闭"},
                col=6,
            ),
            FormItem(
                tag_code="use_ssl",
                type="switch",
                name="SSL 加密",
                name_en="SSL Encryption",
                default=False,
                attrs={"active_text": "开启", "inactive_text": "关闭"},
                col=6,
            ),
            FormItem(
                tag_code="mail_from",
                type="input",
                name="发件人地址",
                name_en="From Address",
                attrs={"placeholder": "noreply@example.com"},
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="mail_to",
                type="textarea",
                name="收件人",
                name_en="Recipients",
                attrs={"rows": 2, "placeholder": "收件人邮箱，多地址用逗号分隔"},
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="subject",
                type="input",
                name="邮件主题",
                name_en="Subject",
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="body",
                type="textarea",
                name="邮件正文",
                name_en="Body",
                attrs={"rows": 6, "placeholder": "支持纯文本或 HTML（取决于 content_type 参数）"},
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="content_type",
                type="select",
                name="内容格式",
                name_en="Content Type",
                default="plain",
                attrs={
                    "options": [
                        {"label": "纯文本 (plain)", "value": "plain"},
                        {"label": "HTML", "value": "html"},
                    ],
                },
                col=6,
            ),
            FormItem(
                tag_code="cc",
                type="input",
                name="抄送",
                name_en="CC",
                attrs={"placeholder": "可选，多地址逗号分隔"},
                col=6,
            ),
        ]

    def execute(self, smtp_host: str, smtp_port: int = 465,
                smtp_user: str = "", smtp_password: str = "",
                use_tls: bool = True, use_ssl: bool = False,
                mail_from: str = "", mail_to: str = "",
                subject: str = "", body: str = "",
                content_type: str = "plain", cc: str = "", **kwargs) -> dict:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = mail_from
            msg['To'] = mail_to
            msg['Subject'] = subject
            if cc:
                msg['Cc'] = cc

            subtype = 'html' if content_type == 'html' else 'plain'
            msg.attach(MIMEText(body, subtype, 'utf-8'))

            recipients = [s.strip() for s in mail_to.split(',') if s.strip()]
            if cc:
                recipients += [s.strip() for s in cc.split(',') if s.strip()]

            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
                if use_tls:
                    server.starttls()

            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)

            server.sendmail(mail_from, recipients, msg.as_string())
            server.quit()

            return {
                "success": True,
                "data": {
                    "from": mail_from,
                    "to": mail_to,
                    "cc": cc or "",
                    "subject": subject,
                    "recipients_count": len(recipients),
                    "sent": True,
                },
            }
        except smtplib.SMTPAuthenticationError:
            return {"success": False, "data": {}, "error": "SMTP 认证失败，请检查用户名或密码"}
        except smtplib.SMTPException as e:
            return {"success": False, "data": {}, "error": f"SMTP 错误: {str(e)}"}
        except Exception as e:
            return {"success": False, "data": {}, "error": f"发送失败: {str(e)}"}
