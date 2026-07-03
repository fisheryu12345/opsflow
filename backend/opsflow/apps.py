import logging

from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


class OpsflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opsflow'
    verbose_name = 'OpsFlow - 运维编排平台'

    def ready(self):
        """注册标准插件 + 变量类型 + 连接信号处理器 + (dev) 调度器自动启动"""
        # 1a) 注册并同步标准插件元数据到 PluginMeta 表
        try:
            from opsflow.plugins.registry import discover_plugins, sync_plugin_meta_to_db
            discover_plugins()
            sync_plugin_meta_to_db()
        except Exception as _e:
            logger.debug("跳过插件注册：%s", str(_e)[:80])

        # 1b) 发现并注册变量类型
        try:
            from opsflow.plugins.registry import discover_variables
            discover_variables()
        except Exception:
            logger.debug("跳过变量类型注册")

        # 2) 连接 BambooDjangoRuntime 信号处理器（节点状态变更 → FlowExecution 更新）
        from opsflow import signals  # noqa
        # 2b) 注册 OpsflowPluginComponent（ComponentMeta 元类在 import 时自动注册到 ComponentLibrary）
        from opsflow.core import plugin_service_adapter  # noqa

        # 3) dev 模式自动启动调度器（仅在非 Celery worker 进程中）
        try:
            from django.conf import settings
            if getattr(settings, 'OPSFLOW_SCHEDULER_AUTOSTART', False):
                # 检查是否在 Celery worker 进程中运行
                import os, sys
                _is_celery_worker = (
                    os.environ.get('CELERY_WORKER_RUNNING') == '1'
                    or (len(sys.argv) > 0 and 'celery' in os.path.basename(sys.argv[0]))
                )
                if _is_celery_worker:
                    logger.info("Celery worker 进程，跳过调度器自动启动")
                else:
                    from opsflow.core.scheduler_service import opsflow_scheduler
                    # Redis 锁防多进程重复启动
                    try:
                        from common.utils.redis_helper import get_redis
                        _r = get_redis(db=0, decode=False)
                        _lock_key = 'lock:opsflow_scheduler'
                        if _r.set(_lock_key, '1', nx=True, ex=60):
                            opsflow_scheduler.start()
                            logger.info("OpsFlow 调度器已自动启动（dev 模式）")
                        else:
                            logger.info("调度器已在其他进程中运行，跳过自动启动")
                    except Exception:
                        # Redis 不可用时降级为直接启动
                        opsflow_scheduler.start()
                        logger.info("OpsFlow 调度器已自动启动（dev 模式，无 Redis 锁）")
        except Exception as e:
            logger.warning(f"OpsFlow 调度器自动启动失败: {e}")
