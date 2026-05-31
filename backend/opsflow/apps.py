import logging

from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


class OpsflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opsflow'
    verbose_name = 'OpsFlow - 运维编排平台'

    def ready(self):
        # 1) 发现并注册标准插件
        try:
            from opsflow.plugins.registry import discover_plugins, sync_plugin_meta_to_db
            discover_plugins()
            sync_plugin_meta_to_db()
        except (ProgrammingError, OperationalError):
            logger.warning("跳过插件注册：数据库表尚未就绪")

        # 2) 连接 BambooDjangoRuntime 信号处理器（节点状态变更 → FlowExecution 更新）
        from opsflow import signals  # noqa

        # 3) dev 模式自动启动调度器
        try:
            from django.conf import settings
            if getattr(settings, 'OPSFLOW_SCHEDULER_AUTOSTART', False):
                from opsflow.core.scheduler_service import opsflow_scheduler
                opsflow_scheduler.start()
                logger.info("OpsFlow 调度器已自动启动（dev 模式）")
        except Exception as e:
            logger.warning(f"OpsFlow 调度器自动启动失败: {e}")
