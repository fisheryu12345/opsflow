import logging

from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)

_SAMPLE_PIPELINE = {
    "nodes": [
        {"id": "node_1", "label": "Start", "node_type": "start_event"},
        {"id": "node_2", "label": "Disk Check", "atom_type": "shell", "node_type": "",
         "params": {"command": "df -h", "timeout": 60}, "max_retries": 1, "retry_delay": 30, "timeout_seconds": 60},
        {"id": "node_3", "label": "End", "node_type": "end_event"},
    ],
    "edges": [
        {"from": "node_1", "to": "node_2", "label": "success"},
        {"from": "node_2", "to": "node_3", "label": "success"},
    ],
}

# Pipeline 2: Nginx health check with exclusive gateway and auto-restore
_NGINX_HEALTH_PIPELINE = {
    "nodes": [
        {"id": "node_1", "label": "Start", "node_type": "start_event"},
        {"id": "node_2", "label": "Health Check Nginx", "atom_type": "health_check", "node_type": "",
         "params": {"host": "web-01", "ping_count": 2, "check_port": True, "port": 80},
         "max_retries": 1, "timeout_seconds": 30},
        {"id": "node_3", "label": "Healthy?", "node_type": "exclusive_gateway"},
        {"id": "node_4", "label": "Report OK", "atom_type": "send_alert", "node_type": "",
         "params": {"channel": "wecom", "title": "Nginx health check passed",
                    "content": "Nginx service on web-01 is healthy.", "recipients": "ops-team"},
         "max_retries": 1, "timeout_seconds": 15},
        {"id": "node_5", "label": "Restart Nginx", "atom_type": "service_control", "node_type": "",
         "params": {"service": "nginx", "action": "restart"},
         "max_retries": 2, "retry_delay": 10, "timeout_seconds": 30},
        {"id": "node_6", "label": "Send Alert", "atom_type": "send_alert", "node_type": "",
         "params": {"channel": "wecom", "title": "Nginx restarted due to failure",
                    "content": "Nginx was down on web-01, auto-restart executed.",
                    "recipients": "ops-team"},
         "max_retries": 1, "timeout_seconds": 15},
        {"id": "node_7", "label": "Converge", "node_type": "converge_gateway"},
        {"id": "node_8", "label": "End", "node_type": "end_event"},
    ],
    "edges": [
        {"from": "node_1", "to": "node_2", "label": "success"},
        {"from": "node_2", "to": "node_3", "label": "success"},
        {"from": "node_3", "to": "node_4", "label": "success"},
        {"from": "node_3", "to": "node_5", "label": "failure"},
        {"from": "node_4", "to": "node_7", "label": "success"},
        {"from": "node_5", "to": "node_6", "label": "success"},
        {"from": "node_5", "to": "node_7", "label": "failure"},
        {"from": "node_6", "to": "node_7", "label": "success"},
        {"from": "node_7", "to": "node_8", "label": "success"},
    ],
}


def _seed_template(project, name: str, category: str, desc: str, pipeline: dict) -> None:
    """Helper: create a sample template if not exists."""
    from opsflow.models import FlowTemplate
    from opsflow.core.node_sync import sync_template_nodes
    tpl, created = FlowTemplate.objects.get_or_create(
        name=name,
        defaults={
            "project": project,
            "category": category,
            "description": desc,
            "is_draft": False,
            "is_public": True,
            "pipeline_tree": pipeline,
            "global_vars": {},
            "version": 1,
        },
    )
    if created:
        tpl.publish_snapshot()
        sync_template_nodes(tpl)
        logger.info("已自动创建示例模板: %s", tpl.name)


def _auto_seed_sample_template():
    """Seed demo templates if not exists."""
    from iam.models import Project as OpsProject
    project, _ = OpsProject.objects.get_or_create(
        name="Demo Project",
        defaults={"description": "Auto-created demo project for onboarding"},
    )
    _seed_template(project, "Quick Start - Disk Check", "system",
                   "Checks disk space via `df -h`. Published and ready to execute.",
                   _SAMPLE_PIPELINE)
    _seed_template(project, "Nginx Health Check and Auto-Restore", "web",
                   "Checks Nginx health on web-01 via ping+port 80. If healthy, reports OK. "
                   "If down, auto-restarts nginx and sends alert. Demonstrates exclusive gateway.",
                   _NGINX_HEALTH_PIPELINE)


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

        # 1b) 发现并注册变量类型
        try:
            from opsflow.plugins.registry import discover_variables
            discover_variables()
        except Exception:
            logger.debug("跳过变量类型注册")

        # 1c) 自动 seed 示例模板（如不存在）
        try:
            _auto_seed_sample_template()
        except Exception:
            logger.debug("跳过示例模板 seed：数据库表尚未就绪或无权限")

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
                        import redis as _redis
                        _r = _redis.Redis(
                            host=getattr(settings, 'REDIS_HOST', '127.0.0.1'),
                            port=getattr(settings, 'REDIS_PORT', 6379),
                            db=0,
                        )
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
