"""
channels.py — ASGI / Channels / WebSocket 配置
"""
from conf.env import *

ASGI_APPLICATION = 'application.asgi.application'

# 使用 RedisChannelLayer 而非 InMemoryChannelLayer，原因：
# ASGI 服务（Daphne/Uvicorn）和 Celery worker 是不同进程，
# InMemoryChannelLayer 跨不了进程，Celery worker 发出的
# WebSocket 消息前端收不到。Redis 作为共享消息通道解决此问题。
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}
