# -*- coding: utf-8 -*-
"""Base connector adapter for Integration Hub

所有连接器适配器必须继承 BaseConnector 并实现 health_check 和 get_client 方法。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class HealthResult:
    """健康检查结果"""
    is_healthy: bool
    message: str = ""


class BaseConnector(ABC):
    """
    连接器基类
    所有适配器必须实现:
    - health_check(): 返回 HealthResult
    - get_client(): 返回外部 SDK 客户端实例
    """

    def __init__(self, instance):
        """
        :param instance: ConnectorInstance ORM 实例
        """
        self.instance = instance
        self._config = instance.config if instance else {}
        self._client = None

    @abstractmethod
    def health_check(self) -> HealthResult:
        """检查外部系统可达性"""
        ...

    @abstractmethod
    def get_client(self) -> Any:
        """获取外部 SDK 客户端"""
        ...

    @property
    def config(self) -> dict:
        return self._config

    def close(self):
        """释放资源（可选覆盖）"""
        self._client = None
