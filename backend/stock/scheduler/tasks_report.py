"""
定期绩效报告生成与发送任务

功能：
- 每月1日09:30 生成上月月度报告
- 每季度第1个月1日09:30 生成上季度季度报告
- 每年1月1日10:00 生成上年度年度报告

依赖：
- stock.infrastructure.pdf_report_generator.generate_report_pdf
- stock.tasks.send_mail.send_report_email_task
"""
import logging
import random
import time
from datetime import date, timedelta

from stock.models import TradingAccount
from stock.infrastructure.pdf_report_generator import generate_report_pdf
from stock.tasks.send_mail import send_report_email_task

logger = logging.getLogger(__name__)


def _get_quarter(month):
    """返回月份对应的季度 (1-4)"""
    return (month - 1) // 3 + 1


def _get_last_month_info(today=None):
    """获取上个月的年和月"""
    today = today or date.today()
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def _get_last_quarter_info(today=None):
    """获取上个季度的年和季度号"""
    today = today or date.today()
    current_q = _get_quarter(today.month)
    if current_q == 1:
        return today.year - 1, 4
    return today.year, current_q - 1


def _get_last_year(today=None):
    """获取上一年"""
    today = today or date.today()
    return today.year - 1


def generate_and_send_report(account_id, report_type, year, month=None, quarter=None):
    """
    生成绩效报告并通过邮件发送

    Args:
        account_id: TradingAccount ID
        report_type: 'monthly', 'quarterly', 'annual'
        year: 年份
        month: 月份（月度报告）
        quarter: 季度（季度报告）
    """
    try:
        account = TradingAccount.objects.get(id=account_id)
    except TradingAccount.DoesNotExist:
        logger.error('账户不存在，跳过报告: id=%s', account_id)
        return

    # 生成 PDF
    pdf_bytes = generate_report_pdf(account_id, report_type, year, month=month, quarter=quarter)

    if pdf_bytes is None:
        logger.error('报告生成失败: %s - %s', account.name, report_type)
        return

    # 构造邮件主题
    if report_type == 'monthly':
        period_str = f'{year}年{month}月'
    elif report_type == 'quarterly':
        period_str = f'{year}年第{quarter}季度'
    else:
        period_str = f'{year}年度'

    subject = f'【绩效报告】{account.name} - {period_str}'
    body = f"""
    <h2>{account.name} - {period_str} 绩效报告</h2>
    <p>您好，附件为本期绩效报告 PDF，请查收。</p>
    <p>报告内容：</p>
    <ul>
        <li>期间收益率、最大回撤、胜率等关键指标</li>
        <li>月度收益明细</li>
        <li>品种盈亏分析</li>
        <li>交易统计</li>
    </ul>
    <p style="color: #999; font-size: 12px;">本报告由量化交易系统自动生成</p>
    """

    # 获取账户邮箱
    receiver_email = None
    try:
        receiver_email = account.user.email if account.user and account.user.email else None
    except Exception:
        pass

    if not receiver_email:
        logger.warning('账户 %s 无关联邮箱，跳过邮件发送', account.name)
        return

    # 发送邮件（同步调用，不依赖 Celery Worker）
    try:
        send_report_email_task(
            subject=subject,
            body=body,
            receiver_email=receiver_email,
            pdf_attachment=pdf_bytes,
        )
    except Exception as e:
        logger.error('报告邮件发送失败: %s - %s', account.name, str(e))

    time.sleep(random.randint(1, 15))  # 随机等待，避免 QQ 邮箱限流

    logger.info('报告邮件已投递: %s - %s -> %s', account.name, period_str, receiver_email)


# ==================== APScheduler Job 入口 ====================

def job_monthly_report():
    """每月1日执行：发送上月月度报告"""
    today = date.today()
    year, month = _get_last_month_info(today)
    logger.info('开始生成月度报告: %s年%s月', year, month)

    accounts = TradingAccount.objects.filter(is_active=True)
    for account in accounts:
        try:
            generate_and_send_report(
                account_id=account.id,
                report_type='monthly',
                year=year,
                month=month,
            )
        except Exception as e:
            logger.error('月度报告生成失败: account=%s, error=%s', account.name, str(e))

    logger.info('月度报告生成完成: %s年%s月, 共%s个账户', year, month, accounts.count())


def job_quarterly_report():
    """每季度首月1日执行：发送上季度季度报告"""
    today = date.today()
    year, quarter = _get_last_quarter_info(today)
    logger.info('开始生成季度报告: %s年第%s季度', year, quarter)

    accounts = TradingAccount.objects.filter(is_active=True)
    for account in accounts:
        try:
            generate_and_send_report(
                account_id=account.id,
                report_type='quarterly',
                year=year,
                quarter=quarter,
            )
        except Exception as e:
            logger.error('季度报告生成失败: account=%s, error=%s', account.name, str(e))

    logger.info('季度报告生成完成: %s年第%s季度, 共%s个账户', year, quarter, accounts.count())


def job_annual_report():
    """每年1月1日执行：发送上年度年度报告"""
    today = date.today()
    year = _get_last_year(today)
    logger.info('开始生成年度报告: %s年', year)

    accounts = TradingAccount.objects.filter(is_active=True)
    for account in accounts:
        try:
            generate_and_send_report(
                account_id=account.id,
                report_type='annual',
                year=year,
            )
        except Exception as e:
            logger.error('年度报告生成失败: account=%s, error=%s', account.name, str(e))

    logger.info('年度报告生成完成: %s年, 共%s个账户', year, accounts.count())
