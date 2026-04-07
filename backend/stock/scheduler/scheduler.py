from apscheduler.schedulers.blocking import BlockingScheduler
from tasks_daily_open import job_daily_open_prep, job_check_pending_orders

scheduler = BlockingScheduler()

# 任务 1: 08:45 计算指标
# 此时夜盘已收盘，日盘未开始，数据最完整
scheduler.add_job(
    job_daily_open_prep, 
    'cron', 
    hour=8, 
    minute=45, 
    id='daily_open_prep',
    name='开盘前指标计算'
)

# 任务 2: 09:00:05 检查跳空
# 开盘后 5 秒，确保有了开盘价
scheduler.add_job(
    job_check_pending_orders, 
    'cron', 
    hour=9, 
    minute=0, 
    second=5,
    id='daily_check_gap',
    name='开盘跳空检查'
)

print("🚀 开盘任务调度器已启动...")
scheduler.start()