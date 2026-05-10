"""
Redis distributed lock with automatic renewal.

Provides a context manager that acquires a Redis lock with a short TTL
and automatically renews it in the background, preventing expiration
during long-running tasks while ensuring crash-safe recovery.
"""
import threading
from contextlib import contextmanager
from typing import Optional


@contextmanager
def redis_lock(redis, lock_key: str, ex: int = 30, renewal_interval: int = 15):
    """
    Redis 分布式锁上下文管理器（带自动续期）

    :param redis: Redis 连接实例（django_redis.get_redis_connection）
    :param lock_key: 锁的键名
    :param ex: 锁的 TTL（秒），默认 30s
    :param renewal_interval: 续期间隔（秒），默认 15s，必须小于 ex
    :raises LockAcquisitionError: 获取锁失败时抛出
    """
    if not redis.set(lock_key, 'true', nx=True, ex=ex):
        raise LockAcquisitionError(lock_key)

    stop_event = threading.Event()

    def _renew():
        while not stop_event.wait(renewal_interval):
            try:
                redis.expire(lock_key, ex)
            except Exception:
                pass

    t = threading.Thread(target=_renew, daemon=True)
    t.start()

    try:
        yield
    finally:
        stop_event.set()
        redis.delete(lock_key)


class LockAcquisitionError(Exception):
    """获取 Redis 分布式锁失败"""

    def __init__(self, lock_key: str):
        self.lock_key = lock_key
        super().__init__(f"无法获取锁 {lock_key}，任务正在其他实例中执行")
