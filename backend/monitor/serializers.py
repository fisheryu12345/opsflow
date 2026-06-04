# -*- coding: utf-8 -*-
"""Serializers for Monitor app

统一规范: 继承 CustomModelSerializer，自动审计字段
"""

from dvadmin.utils.serializers import CustomModelSerializer
from .models.alert import AlertRule, AlertEvent, MonitorTarget


class AlertRuleSerializer(CustomModelSerializer):
    class Meta:
        model = AlertRule
        fields = "__all__"


class AlertRuleCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = AlertRule
        fields = "__all__"


class AlertEventSerializer(CustomModelSerializer):
    class Meta:
        model = AlertEvent
        fields = "__all__"
        read_only_fields = ['alert_id', 'acknowledged_at', 'resolved_at']


class AlertEventAckSerializer(CustomModelSerializer):
    """告警确认 — 仅更新状态"""
    class Meta:
        model = AlertEvent
        fields = ['status', 'acknowledged_by']


class MonitorTargetSerializer(CustomModelSerializer):
    class Meta:
        model = MonitorTarget
        fields = "__all__"
