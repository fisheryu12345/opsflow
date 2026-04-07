import smtplib
from email.mime.text import MIMEText
from email.header import Header

# 邮箱配置
smtp_server = 'smtp.qq.com'
smtp_port = 465
sender_email = '312711936@qq.com'
sender_pass = '你的授权码'  # 不是邮箱密码，是授权码
receiver_email = '312711936@qq.com'

# 邮件内容
subject = '测试邮件'
body = '这是一封通过Python发送的测试邮件。'

# 构建邮件
msg = MIMEText(body, 'plain', 'utf-8')
msg['From'] = Header(sender_email)
msg['To'] = Header(receiver_email)
msg['Subject'] = Header(subject)

# 发送邮件
try:
    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    server.login(sender_email, sender_pass)
    server.sendmail(sender_email, [receiver_email], msg.as_string())
    server.quit()
    print('邮件发送成功')
except Exception as e:
    print('邮件发送失败:', e)