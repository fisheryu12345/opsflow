from django.apps import AppConfig


class StockConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stock'
    def ready(self):
        # 导入调度器和任务
        from django_redis import get_redis_connection
        # from . import tasks # 确保任务函数被导入
        print("正在启动定时任务调度器...")
        redis = get_redis_connection('default')
        lock_key = 'lock:scheduler'
        lock_timeout = 10
        if redis.set(lock_key, 'true', nx=True, ex=lock_timeout):
            from stock.scheduler.scheduler import scheduler
            try:
                # 添加你的定时任务
                # 这里演示每10秒执行一次任务
                # 启动调度器
                if not scheduler.running:
                    scheduler.start()
                    print("启动定时任务成功！")
            finally:
                redis.delete(lock_key)
