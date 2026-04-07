import smtplib
from email.mime.text import MIMEText
from email.header import Header

def send_email(subject, body, receiver_email,
               smtp_server='smtp.qq.com', smtp_port=465,
               sender_email='312711936@qq.com', sender_pass='xkrrvjmgeosycbch'):
    """
    发送邮件的函数
    """
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = Header(sender_email)
    msg['To'] = Header(receiver_email)
    msg['Subject'] = Header(subject)

    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, [receiver_email], msg.as_string())
        server.quit()
        print('邮件发送成功')
    except Exception as e:
        print('邮件发送失败:', e)

# 示例调用
# send_email('测试邮件', '这是一封通过Python发送的测试邮件。', '312711936@qq.com')