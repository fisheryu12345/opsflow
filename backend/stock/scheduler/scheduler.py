from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore


# 交易任务（无外部依赖，始终可用）
from stock.scheduler.tasks_exit_before_close import execute_exit_before_close
from stock.scheduler.tasks_daily_close import job_daily_close_calculation
from stock.scheduler.tasks_daily_open import job_daily_open_process
from stock.scheduler.tasks_daily_commission import job_daily_commission_query
from stock.scheduler.tasks_update_float_profit import job_update_float_profit


scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
scheduler.add_jobstore(DjangoJobStore(), 'default')

# ==================== 交易任务 ====================

scheduler.add_job(
    job_daily_close_calculation,
    'cron',
    day_of_week='mon-fri',
    hour=15,
    minute=32,
    id='job_daily_close_calculation',
    name='盘后指标计算与绩效统计（15:32 执行，确保结算价已最终确定）',
    misfire_grace_time=300,
    replace_existing=True,
    max_instances=1,
)

scheduler.add_job(
    job_daily_open_process,
    'cron',
    day_of_week='mon-fri',
    hour='9,21',
    minute='2',
    id='job_daily_open_process',
    name='开盘前准备与跳空检查',
    misfire_grace_time=300,
    replace_existing=True,
    max_instances=1,
)

scheduler.add_job(
    execute_exit_before_close,
    'cron',
    day_of_week='mon-fri',
    hour='14',
    minute='57',
    id='execute_exit_before_close',
    name='收盘前平仓任务',
    misfire_grace_time=300,
    replace_existing=True,
    max_instances=1,
)

# 每日手续费查询（14:58 — 早于 15:02 收盘计算，提前捕获手续费数据）
scheduler.add_job(
    job_daily_commission_query,
    'cron',
    day_of_week='mon-fri',
    hour=14,
    minute=58,
    id='job_daily_commission_query',
    name='盘前手续费查询',
    misfire_grace_time=300,
    replace_existing=True,
    max_instances=1,
)

# 持仓浮动盈亏更新（周一到周五 10:00/11:00/14:00/22:00/23:00）
scheduler.add_job(
    job_update_float_profit,
    'cron',
    day_of_week='mon-fri',
    hour='10,11,14,22,23',
    minute=0,
    id='job_update_float_profit',
    name='持仓浮动盈亏更新',
    misfire_grace_time=600,
    replace_existing=True,
    max_instances=1,
)

# ==================== 绩效报告任务（依赖 WeasyPrint） ====================

try:
    from stock.scheduler.tasks_report import (
        job_monthly_report,
        job_quarterly_report,
        job_annual_report,
    )
except ImportError:
    import logging
    logging.getLogger(__name__).warning(
        '跳过绩效报告任务注册（tasks_report 导入失败，可能缺少 WeasyPrint）'
    )
else:
    scheduler.add_job(
        job_monthly_report,
        'cron', day=1, hour=9, minute=30,
        id='job_monthly_report',
        name='月度绩效报告',
        misfire_grace_time=3600,
        replace_existing=True, max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        job_quarterly_report,
        'cron', month='1,4,7,10', day=1, hour=9, minute=30,
        id='job_quarterly_report',
        name='季度绩效报告',
        misfire_grace_time=3600,
        replace_existing=True, max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        job_annual_report,
        'cron', month=1, day=1, hour=10, minute=0,
        id='job_annual_report',
        name='年度绩效报告',
        misfire_grace_time=7200,
        replace_existing=True, max_instances=1, coalesce=True,
    )
