import functools
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

from django.conf import settings
from celery import platforms

# # 租户模式
# if "django_tenants" in settings.INSTALLED_APPS:
#     from tenant_schemas_celery.app import CeleryApp as TenantAwareCeleryApp

#     app = TenantAwareCeleryApp()
# else:
from celery import Celery

app = Celery('application')
app.set_default()
# 将本 Celery 实例设为全局默认，使 @shared_task（本质是 @current_app.task()）注册到此实例。
# opsflow/tasks.py 和 stock/tasks/send_mail.py 中的 @shared_task 依赖此行为，
# 否则它们会注册到 Celery 内部无配置的默认实例，导致 broker 配置丢失、任务无法执行。

app.config_from_object('django.conf:settings',namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
platforms.C_FORCE_ROOT = True


def retry_base_task_error():
    """
    celery 失败重试装饰器
    :return:
    """

    def wraps(func):
        @app.task(bind=True, retry_delay=180, max_retries=3)
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                raise self.retry(exc=exc)

        return wrapper

    return wraps
