from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore


# 导入任务函数（使用完整路径）
# from stock.scheduler.tasks_daily_open import job_daily_on_prep, job_check_pending_orders
from stock.scheduler.test_job import test_job
from stock.scheduler.tasks_daily_close import job_daily_close_calculation
from stock.scheduler.tasks_daily_open import job_daily_open_process
from stock.deepseek.ai_control_open_task import check_night_trading_and_sync_config
from stock.utils.update_night_trading import ai_sync_night_trading_status
from backend.stock.scheduler.check_night_trade import sync_night_trading_status_from_tqsdk


# 获取 Django 配置的时区


# 创建调度器并设置中国时区
scheduler = BackgroundScheduler()
#     job_defaults={
#         'coalesce': True,  # 合并错过的执行
#         'max_instances': 1,  # 每个任务最多同时运行1个实例
#         'misfire_grace_time': 300  # 默认容错时间5分钟
#     }
# )
scheduler.remove_all_jobs()
scheduler.add_jobstore(DjangoJobStore(), 'default')
# ==================== 任务调度配置 ====================



scheduler.add_job(
    test_job, 
    'interval', 
    hours=1, 
    id='test_job',
    name='test_job',
    misfire_grace_time=300,  # 允许5分钟的容错时间
    replace_existing=True,  # 如果任务已存在则替换
    max_instances=1  # 最多同时运行1个实例
)

# 任务 1: 每日收盘后计算（16:00）
# 此时日盘已收盘，数据最完整，执行：
# - 同步期货合约列表
# - 计算活跃品种技术指标
# - 计算账户绩效
scheduler.add_job(
    job_daily_close_calculation, 
    'cron', 
    hour=16, 
    minute=0, 
    id='job_daily_close_calculation',
    name='盘后指标计算与绩效统计',
    misfire_grace_time=300,  # 允许5分钟的容错时间
    replace_existing=True,  # 如果任务已存在则替换
    max_instances=1  # 最多同时运行1个实例
)

# 任务 2: AI 智能同步品种夜盘状态（17:30）
# 每天下午5点半自动调用 DeepSeek AI 识别所有品种的夜盘交易状态
# - 批量分析数据库中所有品种的夜盘属性
# - 自动更新 FullContractList.night_trading 字段
# - 基于真实交易所规则，无需人工维护清单
# scheduler.add_job(
#     ai_sync_night_trading_status, 
#     'cron', 
#     hour=17, 
#     minute=30, 
#     id='ai_sync_night_trading_status',
#     name='AI智能同步品种夜盘状态',
#     misfire_grace_time=300,  # 允许5分钟的容错时间
#     replace_existing=True,  # 如果任务已存在则替换
#     max_instances=1  # 最多同时运行1个实例
# )

# 任务 3: 夜盘交易状态检测（18:00）
# 每天下午6点检查次日夜盘是否因节假日休市
# - 调用 AI + 本地日历库判断交易状态
# - 自动更新策略配置 pause_open_task_job
# - 如遇节假日暂停，发送邮件通知
# scheduler.add_job(
#     check_night_trading_and_sync_config, 
#     'cron', 
#     hour=18, 
#     minute=0, 
#     id='check_night_trading_status',
#     name='夜盘交易状态检测与配置同步',
#     misfire_grace_time=300,  # 允许5分钟的容错时间
#     replace_existing=True,  # 如果任务已存在则替换
#     max_instances=1  # 最多同时运行1个实例
# )

# 任务 4: TqSDK 同步品种夜盘状态（每周一 到 周五 早上 8:00）
# 使用 TqSDK API 查询所有期货品种的夜盘交易状态
# - 调用 api.query_quotes(ins_class="FUTURE", has_night=False/True)
# - 自动更新 FullContractList.night_trading 字段
# - 基于 TqSDK 实时数据，确保准确性
scheduler.add_job(
    sync_night_trading_status_from_tqsdk, 
    'cron', 
    day_of_week='mon,tue,wed,thu,fri',
    hour=8, 
    minute=0, 
    id='sync_night_trading_from_tqsdk',
    name='TqSDK同步品种夜盘状态',
    misfire_grace_time=300,  # 允许5分钟的容错时间
    replace_existing=True,  # 如果任务已存在则替换
    max_instances=1  # 最多同时运行1个实例
)

scheduler.add_job(
    job_daily_open_process, 
    'cron', 
    hour=21, 
    minute=1, 
    id='job_daily_open_process',
    name='开盘前准备与跳空检查',
    misfire_grace_time=300,  # 允许5分钟的容错时间
    replace_existing=True,
    max_instances=1
)
