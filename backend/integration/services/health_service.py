# -*- coding: utf-8 -*-
"""Health check service for Integration Hub

健康检查 — 定期检测连接器实例的可达性和状态
"""

import logging
from datetime import datetime

from django.utils import timezone

logger = logging.getLogger(__name__)


def run_health_check(instance) -> tuple:
    """
    对单个连接器实例执行健康检查
    返回 (is_healthy: bool, message: str)
    """
    definition = instance.definition
    provider_path = definition.provider_class

    if not provider_path:
        # 无适配器，仅做连接测试
        return _basic_health_check(instance)

    try:
        provider_class = _import_provider(provider_path)
        provider = provider_class(instance)
        result = provider.health_check()
        return result.is_healthy, result.message
    except ImportError:
        logger.warning(f"适配器 {provider_path} 未找到，执行基础检查")
        return _basic_health_check(instance)
    except Exception as e:
        logger.error(f"健康检查异常 [{instance.name}]: {e}")
        return False, str(e)


def _basic_health_check(instance) -> tuple:
    """无适配器时的基础健康检查"""
    if not instance.health_check_url:
        return True, "未配置健康检查"
    # 简单 URL 可达性检查
    try:
        import requests
        resp = requests.get(instance.health_check_url, timeout=10)
        if resp.ok:
            return True, f"HTTP {resp.status_code}"
        return False, f"HTTP {resp.status_code}"
    except ImportError:
        return True, "需要 requests 库执行 HTTP 健康检查"
    except Exception as e:
        return False, str(e)


def _import_provider(path: str):
    """动态导入适配器类"""
    from importlib import import_module
    module_path, class_name = path.rsplit('.', 1)
    module = import_module(module_path)
    return getattr(module, class_name)


class HealthCheckScheduler:
    """健康检查调度器 — 定时批量检查所有活跃实例"""

    @classmethod
    def run_all(cls):
        """对所有活跃实例执行健康检查"""
        from integration.models.connector import ConnectorInstance
        instances = ConnectorInstance.objects.filter(is_active=True)
        for inst in instances:
            healthy, msg = run_health_check(inst)
            inst.status = 'online' if healthy else 'error'
            inst.last_health_check = timezone.now()
            inst.last_health_message = msg
            inst.save(update_fields=['status', 'last_health_check', 'last_health_message'])
        return len(instances)
