from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore


# 导入任务函数（使用完整路径）
# from stock.scheduler.tasks_daily_open import job_daily_on_prep, job_check_pending_orders
# from stock.scheduler.test_job import test_job
from stock.scheduler.tasks_exit_before_close import execute_exit_before_close
from stock.scheduler.tasks_daily_close import job_daily_close_calculation
from stock.scheduler.tasks_daily_open import job_daily_open_process



# 获取 Django 配置的时区


# 创建调度器并设置中国时区
scheduler = BackgroundScheduler()
#     job_defaults={
#         'coalesce': True,  # 合并错过的执行
#         'max_instances': 1,  # 每个任务最多同时运行1个实例
#         'misfire_grace_time': 300  # 默认容错时间5分钟
#     }
# )
scheduler = BackgroundScheduler(timezone='Asia/Shanghai') # 【关键修复】
scheduler.remove_all_jobs()
scheduler.add_jobstore(DjangoJobStore(), 'default')
# ==================== 任务调度配置 ====================



# scheduler.add_job(
#     test_job, 
#     'interval', 
#     hours=3, 
#     id='test_job',
#     name='test_job',
#     misfire_grace_time=300,  # 允许5分钟的容错时间
#     replace_existing=True,  # 如果任务已存在则替换
#     max_instances=1  # 最多同时运行1个实例
# )

# 任务 1: 每日收盘后计算（16:00）
# 此时日盘已收盘，数据最完整，执行：
# - 同步期货合约列表
# - 计算活跃品种技术指标
# - 计算账户绩效
scheduler.add_job(
    job_daily_close_calculation, 
    'cron', 
    day_of_week='mon-fri',  # 周一到周五
    hour=15, 
    minute=2, 
    id='job_daily_close_calculation',
    name='盘后指标计算与绩效统计',
    misfire_grace_time=300,  # 允许5分钟的容错时间
    replace_existing=True,  # 如果任务已存在则替换
    max_instances=1  # 最多同时运行1个实例
)

# 任务 2: 每日开盘前处理（周一至周五 09:02 和 21:02）
# 此时市场即将开盘，执行：
# - 检查并执行止损信号
# - 检查并执行开仓信号
# - 检查并执行移仓信号
# - 检查并执行加仓信号
scheduler.add_job(
    job_daily_open_process, 
    'cron', 
    day_of_week='mon-fri',  # 周一到周五
    hour='9,21',  # 早上9点和晚上21点
    minute='2',  # 第2分钟
    id='job_daily_open_process',
    name='开盘前准备与跳空检查',
    misfire_grace_time=300,  # 允许5分钟的容错时间
    replace_existing=True,
    max_instances=1
)


scheduler.add_job(
    execute_exit_before_close, 
    'cron', 
    day_of_week='mon-fri',  # 周一到周五
    hour='14',  # 早上9点和晚上21点
    minute='57',  # 第2分钟
    id='execute_exit_before_close',
    name='收盘前平仓任务',
    misfire_grace_time=300,  # 允许5分钟的容错时间
    replace_existing=True,
    max_instances=1
)
