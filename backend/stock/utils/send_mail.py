import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.header import Header

from celery import shared_task

logger = logging.getLogger(__name__)
@shared_task()
def send_email(subject, body, receiver_email,
               smtp_server='smtp.qq.com', smtp_port=465,
               sender_email=None, sender_pass=None,
               is_html=True):
    """
    发送邮件的函数
    
    Args:
        subject: 邮件主题
        body: 邮件正文
        receiver_email: 收件人邮箱
        smtp_server: SMTP服务器地址
        smtp_port: SMTP服务器端口
        sender_email: 发件人邮箱
        sender_pass: 发件人授权码
        is_html: 是否为HTML格式，默认为True（HTML格式）
    
    Returns:
        bool: 发送成功返回True，失败返回False
    """
    if sender_email is None:
        sender_email = os.getenv('EMAIL_SENDER', '312711936@qq.com')
    if sender_pass is None:
        sender_pass = os.getenv('EMAIL_PASSWORD', 'xkrrvjmgeosycbch')
    
    if not receiver_email or not subject or not body:
        logger.error('邮件发送失败: 缺少必要参数')
        return False
    
    content_type = 'html' if is_html else 'plain'
    msg = MIMEText(body, content_type, 'utf-8')
    msg['From'] = Header(sender_email)
    msg['To'] = Header(receiver_email)
    msg['Subject'] = Header(subject)

    server = None
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, [receiver_email], msg.as_string())
        logger.info('邮件发送成功')
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error('邮件发送失败: 认证错误，请检查邮箱账号和授权码')
        return False
    except smtplib.SMTPConnectError:
        logger.error('邮件发送失败: 无法连接到SMTP服务器')
        return False
    except smtplib.SMTPException as e:
        logger.error('邮件发送失败: SMTP错误 - %s', str(e))
        return False
    except Exception as e:
        logger.error('邮件发送失败: %s', str(e))
        return False
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass