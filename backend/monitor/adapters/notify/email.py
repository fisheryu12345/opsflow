# -*- coding: utf-8 -*-
"""Email notify adapter — 通过 SMTP 发送告警邮件"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .. import BaseNotifyAdapter, NotifyMessage, NotifyResult

logger = logging.getLogger(__name__)
FSM = 'email_adapter'


class EmailNotify(BaseNotifyAdapter):
    """邮件通知适配器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.smtp_host = config.get('smtp_host', '')
        self.smtp_port = config.get('smtp_port', 465)
        self.smtp_user = config.get('smtp_user', '')
        self.smtp_password = config.get('smtp_password', '')
        self.use_ssl = config.get('use_ssl', True)
        self.from_addr = config.get('from_addr', self.smtp_user)

    def send(self, recipients: list, message: NotifyMessage) -> NotifyResult:
        if not self.smtp_host or not recipients:
            return NotifyResult(success=False, message='SMTP not configured')

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[Monitor] {message.title}"
        msg['From'] = self.from_addr
        msg['To'] = ', '.join(recipients)

        html = f"""<html><body>
<h2>{message.title}</h2>
<p>级别: {'🔴 致命' if message.severity == 1 else '🟡 预警' if message.severity == 2 else '🔵 提醒'}</p>
<pre>{message.content}</pre>
<hr><small>告警ID: {message.alert_id}</small></body></html>"""
        msg.attach(MIMEText(html, 'html'))

        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
                server.starttls()
            if self.smtp_user:
                server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_addr, recipients, msg.as_string())
            server.quit()
            return NotifyResult(success=True, message='Sent')
        except Exception as e:
            logger.error(f"[Email] Send failed: {e}")
            return NotifyResult(success=False, message=str(e))
