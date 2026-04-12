from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore


# 导入任务函数（使用完整路径）
# from stock.scheduler.tasks_daily_open import job_daily_on_prep, job_check_pending_orders
from stock.scheduler.test_job import test_job
from stock.scheduler.tasks_daily_close import job_daily_close_calculation


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


# 任务 2: 每日开盘前准备（08:45）
# 此时夜盘已收盘，日盘未开始，执行：
# - 检查跳空缺口
# - 处理待执行订单
# scheduler.add_job(
#     job_daily_open_prep, 
#     'cron', 
#     hour=8, 
#     minute=45, 
#     id='job_daily_open_prep',
#     name='开盘前准备与跳空检查',
#     misfire_grace_time=300,  # 允许5分钟的容错时间
#     replace_existing=True,
#     max_instances=1
# )
# logger.info("✅ 已添加任务: 开盘前准备 (每天 08:45)")

# 任务 3: 开盘后立即检查待执行订单（09:00:05）
# 开盘后 5 秒，确保有了开盘价
# scheduler.add_job(
#     job_check_pending_orders, 
#     'cron', 
#     hour=9, 
#     minute=0, 
#     second=5,
#     id='job_check_pending_orders',
#     name='开盘后执行待处理订单',
#     misfire_grace_time=60,  # 允许1分钟的容错时间
#     replace_existing=True,
#     max_instances=1
# )
# logger.info("✅ 已添加任务: 执行待处理订单 (每天 09:00:05)")

# print("="*70)
# print("📋 任务列表:")
# for job in scheduler.get_jobs():
#     print(f"   - {job.name}")
#     print(f"     ID: {job.id}")
#     print(f"     触发器: {job.trigger}")
#     print(f"     下次执行: {job.next_run_time}")
#     print()
# print("="*70)

# print("\n⏰ 调度器正在运行... (按 Ctrl+C 停止)\n")
# logger.info("调度器已启动，等待任务执行...")

# try:
#     scheduler.start()
# except (KeyboardInterrupt, SystemExit):
#     pass
