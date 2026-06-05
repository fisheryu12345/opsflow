# -*- coding: utf-8 -*-
"""Email (SMTP) notification adapter

邮件通知适配器 — 通过 SMTP 服务发送邮件

配置项:
  - host: SMTP 服务器
  - port: 端口（默认 465）
  - use_ssl: 是否使用 SSL（默认 True）
  - from_address: 发件地址

凭证（ConnectorCredential）:
  - cred_type=password: SMTP 登录密码或授权码
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from integration.adapters.base import BaseConnector, HealthResult
from integration.services.credential_service import decrypt_credential

logger = logging.getLogger(__name__)


class EmailSmtpConnector(BaseConnector):
    """
    SMTP 邮件适配器

    使用 smtplib 发送邮件，支持 SSL/TLS。
    密码存储在 ConnectorCredential 中（cred_type=password）。
    """

    def get_client(self):
        """创建并缓存 SMTP 连接"""
        if self._client:
            return self._client

        host = self.config.get('host', '')
        port = int(self.config.get('port', 465))
        use_ssl = self.config.get('use_ssl', True)

        if not host:
            raise ValueError("SMTP 服务器地址未配置")

        # 解密凭证
        username = self.config.get('from_address', '')
        cred = self.instance.credentials.filter(
            cred_type__in=['password', 'custom']
        ).first()
        password = decrypt_credential(cred.encrypted_value) if cred else ''

        try:
            if use_ssl:
                client = smtplib.SMTP_SSL(host, port, timeout=15)
            else:
                client = smtplib.SMTP(host, port, timeout=15)
                client.starttls()

            if password:
                client.login(username, password)

            self._client = client
            return client
        except smtplib.SMTPException as e:
            raise RuntimeError(f"SMTP 连接失败: {e}") from e

    def health_check(self) -> HealthResult:
        """通过连接 SMTP 服务器并 EHLO 来检查可达性"""
        host = self.config.get('host', '')
        if not host:
            return HealthResult(is_healthy=False, message="未配置 SMTP 服务器地址")

        try:
            client = self.get_client()
            if client:
                # Verify connection with a noop
                client.noop()
                return HealthResult(is_healthy=True, message=f"SMTP {host} 连接正常")
            return HealthResult(is_healthy=False, message="客户端创建失败")
        except ImportError:
            return HealthResult(is_healthy=False, message="smtplib 不可用")
        except Exception as e:
            return HealthResult(is_healthy=False, message=str(e))

    def send_email(self, to_addrs: list[str], subject: str,
                   body: str, body_type: str = 'plain',
                   cc_addrs: list[str] = None) -> dict:
        """发送邮件

        Args:
            to_addrs: 收件人地址列表
            subject: 邮件主题
            body: 邮件正文
            body_type: 'plain' 或 'html'
            cc_addrs: 抄送地址列表

        Returns:
            {'success': True, 'message': '...'}
        """
        client = self.get_client()
        from_addr = self.config.get('from_address', '')
        if not from_addr:
            raise ValueError("发件地址未配置")

        msg = MIMEMultipart('alternative')
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = Header(subject, 'utf-8')

        if cc_addrs:
            msg['Cc'] = ', '.join(cc_addrs)
            to_addrs = list(to_addrs) + list(cc_addrs)

        msg.attach(MIMEText(body, body_type, 'utf-8'))

        try:
            client.sendmail(from_addr, to_addrs, msg.as_string())
            logger.info(f"邮件发送成功 [{', '.join(to_addrs)}]: {subject}")
            return {'success': True, 'message': f'邮件已发送至 {len(to_addrs)} 个收件人'}
        except smtplib.SMTPException as e:
            logger.error(f"邮件发送失败: {e}")
            raise RuntimeError(f"邮件发送失败: {e}") from e

    def close(self):
        """关闭 SMTP 连接"""
        if self._client:
            try:
                self._client.quit()
            except Exception:
                self._client.close()
            self._client = None
