# -*- coding: utf-8 -*-
"""Alert convergence engine — dedup, aggregation, suppression

告警收敛引擎 — 去重、聚合、抑制，防止告警风暴
"""

import logging
from datetime import timedelta

from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

FSM = 'alert_convergence'


def dedup_alert(alert_event) -> bool:
    """
    告警去重检查
    返回 True 表示此告警与已有告警重复，应丢弃
    """
    # 基于 alert_id 去重
    from ..models.alert import AlertEvent
    dup = AlertEvent.objects.filter(
        alert_id=alert_event.get('alert_id', ''),
        status__in=['firing', 'acknowledged'],
    ).exists()
    return dup


def aggregate_alerts(window_minutes: int = 10) -> int:
    """
    告警聚合 — 将相同规则、相同主机的重复告警聚合成一条
    返回聚合处理的数量
    """
    from ..models.alert import AlertEvent
    cutoff = timezone.now() - timedelta(minutes=window_minutes)
    # 标记同一规则+同一主机的多次触发为已聚合
    aggregated = 0
    recent = AlertEvent.objects.filter(fired_at__gte=cutoff, status='firing').order_by('rule', 'cmdb_host_id')
    seen = set()
    for event in recent:
        key = (event.rule_id, event.cmdb_host_id)
        if key in seen:
            event.status = 'silenced'
            event.save(update_fields=['status'])
            aggregated += 1
        else:
            seen.add(key)
    return aggregated


def suppress_by_rule(rule_id: int, duration_minutes: int = 60) -> int:
    """
    告警抑制 — 某个规则触发后，在 duration_minutes 内不再重复告警
    """
    from ..models.alert import AlertEvent
    cutoff = timezone.now() - timedelta(minutes=duration_minutes)
    suppressed = AlertEvent.objects.filter(
        rule_id=rule_id,
        fired_at__gte=cutoff,
        status='firing',
    ).exclude(status='silenced').update(status='silenced')
    return suppressed
