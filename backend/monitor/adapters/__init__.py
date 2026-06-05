# -*- coding: utf-8 -*-
"""SPI Adapter base interfaces — 数据源/通知/动作/目标解析四类适配器基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
# 通用类型定义
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class MetricValue:
    """指标值"""
    metric: str
    value: float
    timestamp: float
    tags: dict = field(default_factory=dict)


@dataclass
class HealthResult:
    """健康检查结果"""
    is_healthy: bool
    message: str = ''


@dataclass
class NotifyMessage:
    """通知消息"""
    title: str
    content: str
    severity: int = 3
    alert_id: str = ''


@dataclass
class NotifyResult:
    """通知结果"""
    success: bool
    message: str = ''


@dataclass
class ActionContext:
    """动作执行上下文"""
    alert_id: str
    alert_title: str
    severity: int
    config: dict


@dataclass
class ActionResult:
    """动作执行结果"""
    success: bool
    message: str = ''


@dataclass
class MonitorTarget:
    """监控目标"""
    target_id: str
    target_type: str  # host / service / instance
    name: str
    address: str = ''


# ═══════════════════════════════════════════════════════════════════════
# 适配器基类
# ═══════════════════════════════════════════════════════════════════════

class BaseDataSourceAdapter(ABC):
    """
    数据源适配器 — 对接 Prometheus/InfluxDB/自建采集
    配置通过 connector 管理（Integration Hub 复用）
    """

    def __init__(self, config: dict):
        self.config = config
        self._client = None

    @abstractmethod
    def fetch_metrics(self, query_config: dict) -> list:
        """查询指标数据"""
        pass

    @abstractmethod
    def health_check(self) -> HealthResult:
        """检查数据源连接"""
        pass

    def get_client(self):
        """获取客户端（子类实现）"""
        return self._client


class BaseNotifyAdapter(ABC):
    """
    通知适配器 — 企业微信/钉钉/邮件/短信
    对接 Integration Hub 的连接器实例管理配置和凭据
    """

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def send(self, recipients: list, message: NotifyMessage) -> NotifyResult:
        """发送通知"""
        pass


class BaseActionAdapter(ABC):
    """
    动作适配器 — OpsFlow 流程/ AWX 作业/ITSM 工单
    执行告警触发的自动化动作
    """

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def execute(self, context: ActionContext) -> ActionResult:
        """执行自动化动作"""
        pass


class BaseTargetResolver(ABC):
    """
    监控目标解析器 — 从 CMDB/容器标签/静态列表解析目标
    """

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def resolve(self, target_expr: dict) -> list:
        """将表达式解析为具体目标列表"""
        pass
