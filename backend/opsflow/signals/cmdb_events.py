"""CMDB 变更事件 — CMDB 数据变更时触发 Pipeline 或 Webhook

支持场景:
  - 新主机上线 → 自动触发"初始化监控 + 安装 Agent"工作流
  - 主机状态变为告警 → 自动触发"自愈"工作流
  - 业务下线 → 自动触发"备份 + 清理"工作流

使用方式:
  from opsflow.signals.cmdb_events import CmdbEventEmitter
  CmdbEventEmitter.emit('host_created', {'instance_id': '...', 'ip': '...'})
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CmdbEventEmitter:
    """CMDB 变更事件发射器

    当 CMDB 数据发生变更时，调用 emit() 通知已注册的 webhooks 和 schedule plans。
    """

    EVENT_TYPES = {
        "host_created": "主机创建",
        "host_updated": "主机更新",
        "host_deleted": "主机删除",
        "host_status_changed": "主机状态变更",
        "biz_created": "业务创建",
        "biz_updated": "业务更新",
        "biz_deleted": "业务删除",
        "relation_created": "关联创建",
        "relation_deleted": "关联删除",
    }

    @classmethod
    def emit(cls, event_type: str, instance_data: dict, extra: dict = None):
        """发射 CMDB 变更事件

        Args:
            event_type: 事件类型，如 'host_created'
            instance_data: 涉及的实例数据（含 instance_id、model_code 等）
            extra: 额外上下文（可选）
        """
        logger.info(
            f"CMDB 事件: [{event_type}] "
            f"{instance_data.get('__model_code', '')} "
            f"{instance_data.get('name') or instance_data.get('ip') or instance_data.get('instance_id', '')}"
        )

        # 1. 查找匹配的 Webhook 配置
        cls._dispatch_webhooks(event_type, instance_data, extra)

        # 2. 查找匹配的 Schedule Plan（通过 CMDBChange 触发器）
        cls._dispatch_pipelines(event_type, instance_data, extra)

    @classmethod
    def _dispatch_webhooks(cls, event_type: str, instance_data: dict, extra: dict = None):
        """触发现有 Webhook 配置中监听 CMDB 事件的条目"""
        try:
            from opsflow.models import WebhookConfig, WebhookLog

            webhooks = WebhookConfig.objects.filter(
                enabled=True,
                trigger_events__contains=event_type,
            )
            for wh in webhooks:
                payload = {
                    "event_type": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "instance": instance_data,
                    "extra": extra or {},
                }
                # 记录 webhook 日志（实际调用由 webhook_service 处理）
                WebhookLog.objects.create(
                    webhook=wh,
                    event=event_type,
                    status="pending",
                    request_url=wh.url,
                    request_body=json.dumps(payload, ensure_ascii=False),
                )
                logger.debug(f"  Webhook 队列: {wh.name} → {wh.url}")
        except Exception as e:
            logger.warning(f"Webhook 分发失败: {e}")

    @classmethod
    def _dispatch_pipelines(cls, event_type: str, instance_data: dict, extra: dict = None):
        """触发监听 CMDB 事件的 Schedule Plan"""
        try:
            from opsflow.models import SchedulePlan
            from opsflow.core.scheduler_service import _execute_plan

            plans = SchedulePlan.objects.filter(
                is_active=True,
                status=SchedulePlan.Status.ACTIVE,
                schedule_type='cmdb_event',
            )
            for plan in plans:
                # 从 description 解析事件配置
                config = {}
                if plan.description:
                    try:
                        config = json.loads(plan.description)
                    except (json.JSONDecodeError, TypeError):
                        config = {"watch_events": [plan.description]}

                watch_events = config.get("watch_events", [])
                if watch_events and event_type not in watch_events:
                    continue

                logger.info(f"  Pipeline 触发: {plan.name}")
                # 直接调用 _execute_plan（APScheduler 的内部回调）
                _execute_plan(plan.id)
        except Exception as e:
            logger.warning(f"Pipeline 触发失败: {e}")
