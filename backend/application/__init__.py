import pymysql

pymysql.install_as_MySQLdb()

# ------------------------------------------------------------------ #
#  重要: 加载 Celery 应用实例
#  缺少此导入时, Django 进程中 celery task 的 delay() / apply_async()
#  无法获取 broker_url 等配置, 会回退到默认 AMQP(localhost:5672)
#  导致 WinError 10061 连接被拒绝错误
# ------------------------------------------------------------------ #
from .celery import app as celery_app

__all__ = ('celery_app',)