import logging
import time

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '启动 OpsFlow 调度器进程（独立运行，非 Celery worker）'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('正在启动 OpsFlow 调度器...'))

        # Redis 锁防重复启动
        try:
            import redis
            from django.conf import settings
            r = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', '127.0.0.1'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
            )
            lock_key = 'lock:opsflow_scheduler'
            if not r.set(lock_key, '1', nx=True, ex=60):
                self.stdout.write(self.style.WARNING('OpsFlow 调度器已在运行中（持有锁），退出'))
                return
        except Exception as e:
            logger.warning(f"Redis 锁检查失败（调度器仍将启动）: {e}")

        from opsflow.core.scheduler_service import opsflow_scheduler
        opsflow_scheduler.start()
        self.stdout.write(self.style.SUCCESS('OpsFlow 调度器已启动'))

        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            opsflow_scheduler.shutdown()
            self.stdout.write(self.style.SUCCESS('OpsFlow 调度器已停止'))
