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

# 示例调用
# send_email('测试邮件', '这是一封通过Python发送的测试邮件。', '312711936@qq.com')

# Complex HTML email example
# html_content = '''
# <!DOCTYPE html>
# <html>
# <head>
#     <meta charset="UTF-8">
#     <style>
#         body {
#             font-family: 'Microsoft YaHei', Arial, sans-serif;
#             line-height: 1.6;
#             color: #333;
#             max-width: 600px;
#             margin: 0 auto;
#             padding: 20px;
#         }
#         .header {
#             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#             color: white;
#             padding: 30px;
#             text-align: center;
#             border-radius: 10px 10px 0 0;
#         }
#         .content {
#             background-color: #f9f9f9;
#             padding: 30px;
#             border: 1px solid #e0e0e0;
#         }
#         .highlight {
#             background-color: #fff3cd;
#             padding: 15px;
#             border-left: 4px solid #ffc107;
#             margin: 20px 0;
#         }
#         .data-table {
#             width: 100%;
#             border-collapse: collapse;
#             margin: 20px 0;
#             background-color: white;
#         }
#         .data-table th {
#             background-color: #667eea;
#             color: white;
#             padding: 12px;
#             text-align: left;
#         }
#         .data-table td {
#             padding: 10px;
#             border-bottom: 1px solid #ddd;
#         }
#         .data-table tr:hover {
#             background-color: #f5f5f5;
#         }
#         .button {
#             display: inline-block;
#             padding: 12px 30px;
#             background-color: #667eea;
#             color: white;
#             text-decoration: none;
#             border-radius: 5px;
#             margin: 20px 0;
#         }
#         .footer {
#             text-align: center;
#             padding: 20px;
#             color: #666;
#             font-size: 12px;
#             border-top: 1px solid #e0e0e0;
#         }
#         .badge {
#             display: inline-block;
#             padding: 5px 10px;
#             background-color: #28a745;
#             color: white;
#             border-radius: 3px;
#             font-size: 12px;
#         }
#     </style>
# </head>
# <body>
#     <div class="header">
#         <h1>📊 股票监控报告</h1>
#         <p>每日市场分析与提醒</p>
#     </div>
    
#     <div class="content">
#         <h2>尊敬的投资者，您好！</h2>
#         <p>以下是今日的股票市场监控报告：</p>
        
#         <div class="highlight">
#             <strong>⚠️ 重要提醒：</strong> 以下数据仅供参考，投资需谨慎。
#         </div>
        
#         <h3>📈 今日重点关注股票</h3>
#         <table class="data-table">
#             <thead>
#                 <tr>
#                     <th>股票代码</th>
#                     <th>股票名称</th>
#                     <th>当前价格</th>
#                     <th>涨跌幅</th>
#                     <th>状态</th>
#                 </tr>
#             </thead>
#             <tbody>
#                 <tr>
#                     <td>600519</td>
#                     <td>贵州茅台</td>
#                     <td>¥1,850.00</td>
#                     <td style="color: #28a745;">+2.35%</td>
#                     <td><span class="badge">上涨</span></td>
#                 </tr>
#                 <tr>
#                     <td>000858</td>
#                     <td>五粮液</td>
#                     <td>¥168.50</td>
#                     <td style="color: #dc3545;">-1.20%</td>
#                     <td><span class="badge" style="background-color: #dc3545;">下跌</span></td>
#                 </tr>
#                 <tr>
#                     <td>600036</td>
#                     <td>招商银行</td>
#                     <td>¥38.75</td>
#                     <td style="color: #28a745;">+0.85%</td>
#                     <td><span class="badge">上涨</span></td>
#                 </tr>
#             </tbody>
#         </table>
        
#         <h3>🎯 技术指标分析</h3>
#         <ul>
#             <li><strong>MACD:</strong> 金叉形成，建议关注买入机会</li>
#             <li><strong>KDJ:</strong> J值处于超买区域，注意回调风险</li>
#             <li><strong>成交量:</strong> 较昨日放大 25%，市场活跃度提升</li>
#         </ul>
        
#         <h3>💡 投资建议</h3>
#         <ol>
#             <li>建议控制仓位在 60% 以下</li>
#             <li>关注蓝筹股的配置机会</li>
#             <li>设置好止损位，严格执行纪律</li>
#         </ol>
        
#         <div style="text-align: center;">
#             <a href="#" class="button">查看详细分析报告</a>
#         </div>
#     </div>
    
#     <div class="footer">
#         <p>此邮件由股票监控系统自动发送</p>
#         <p>© 2024 股票监控系统 | 如有疑问请联系客服</p>
#         <p style="color: #999; font-size: 11px;">
#             免责声明：本邮件内容不构成投资建议，股市有风险，投资需谨慎。
#         </p>
#     </div>
# </body>
# </html>
# '''

# # 使用示例
# if __name__ == '__main__':
#     send_email(
#         subject='📊 今日股票监控报告 - 2024年',
#         body=html_content,
#         receiver_email='312711936@qq.com',
#         is_html=True  # 默认就是True，可以省略
#     )