"""Ansible Tower (AWX) REST API 服务封装 — 插件后端执行引擎"""
from typing import Optional
from opsflow.plugins.ansible.tower_backend.client import TowerClientMixin
from opsflow.plugins.ansible.tower_backend.job import TowerJobMixin
from opsflow.plugins.ansible.tower_backend.polling import TowerPollingMixin
from opsflow.plugins.ansible.tower_backend.base import TowerConfigError, TowerJobError, TowerTimeoutError

__all__ = [
    'TowerService', 'get_tower_service',
    'TowerConfigError', 'TowerJobError', 'TowerTimeoutError',
]


class TowerService(TowerClientMixin, TowerJobMixin, TowerPollingMixin):
    """Ansible Tower (AWX) REST API 服务

    职责:
      - 触发 Job Template 执行
      - 主动轮询作业状态（自适应间隔）
      - 提取执行结果 (artifacts / events / stdout)
      - 通过 WebSocket 推送实时状态
      - 取消运行中的作业
    """

    def __init__(self):
        self._session: Optional['requests.Session'] = None
        self._config: Optional[dict] = None
        self._load_config()


import requests  # noqa: E402


# 全局单例
_tower_service: Optional[TowerService] = None


def get_tower_service() -> TowerService:
    """获取 TowerService 单例"""
    global _tower_service
    if _tower_service is None:
        _tower_service = TowerService()
    return _tower_service
