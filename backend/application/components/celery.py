"""
celery.py — Celery 任务队列配置

包括 Broker、Backend、队列路由、任务序列化等。
"""
from kombu import Queue
from conf.env import *

CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'
CELERY_TASK_DEFAULT_QUEUE = 'default'

CELERY_TASK_QUEUES = [
    Queue('default', routing_key='default'),
    Queue('er_execute', routing_key='er_execute'),
    Queue('er_schedule', routing_key='er_schedule'),
]

DJANGO_CELERY_BEAT_TZ_AWARE = False
CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_RESULT_SERIALIZER = "json"
