# -*- coding: utf-8 -*-
"""Serializers for Monitor app — 所有模型的序列化器

遵循 opsflow 规范: 继承 CustomModelSerializer，自动审计字段
"""

from common.utils.serializers import CustomModelSerializer
from rest_framework import serializers

from .models import (
    MonitorStrategy, MonitorItem, MonitorQueryConfig,
    MonitorDetectConfig, MonitorAlgorithmConfig,
    MonitorStrategyLabel, MonitorStrategyHistory,
    AlertEvent, Alert, AlertLog,
    NotifyGroup, DutyPlan, DutyArrange, NotifyConfig,
    AlertAssignGroup, AlertAssignRule, ActionPlugin,
    ShieldPlan, CollectConfig,
)


# ═══════════════════════════════════════════════════════════════════════
# 策略层
# ═══════════════════════════════════════════════════════════════════════

class MonitorAlgorithmConfigSerializer(CustomModelSerializer):
    class Meta:
        model = MonitorAlgorithmConfig
        fields = "__all__"


class MonitorDetectConfigSerializer(CustomModelSerializer):
    algorithms = MonitorAlgorithmConfigSerializer(many=True, read_only=True)

    class Meta:
        model = MonitorDetectConfig
        fields = "__all__"


class MonitorQueryConfigSerializer(CustomModelSerializer):
    class Meta:
        model = MonitorQueryConfig
        fields = "__all__"


class MonitorItemSerializer(CustomModelSerializer):
    query_configs = MonitorQueryConfigSerializer(many=True, read_only=True)
    detect_configs = MonitorDetectConfigSerializer(many=True, read_only=True)

    class Meta:
        model = MonitorItem
        fields = "__all__"


class MonitorStrategyListSerializer(CustomModelSerializer):
    """策略列表 — 精简版"""
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = MonitorStrategy
        fields = "__all__"

    def get_item_count(self, obj):
        return obj.items.count()


class MonitorStrategyDetailSerializer(CustomModelSerializer):
    """策略详情 — 嵌套所有子级"""
    items = MonitorItemSerializer(many=True, read_only=True)
    labels = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = MonitorStrategy
        fields = "__all__"


class MonitorStrategyCreateUpdateSerializer(CustomModelSerializer):
    """创建/更新策略 — 支持嵌套创建 items+detects+algorithms"""

    class Meta:
        model = MonitorStrategy
        fields = "__all__"


class MonitorStrategyLabelSerializer(CustomModelSerializer):
    class Meta:
        model = MonitorStrategyLabel
        fields = "__all__"


class MonitorStrategyHistorySerializer(CustomModelSerializer):
    class Meta:
        model = MonitorStrategyHistory
        fields = "__all__"


# ═══════════════════════════════════════════════════════════════════════
# 告警事件层
# ═══════════════════════════════════════════════════════════════════════

class AlertEventSerializer(CustomModelSerializer):
    """原始事件 — 只读"""
    class Meta:
        model = AlertEvent
        fields = "__all__"
        read_only_fields = [f.name for f in AlertEvent._meta.fields]


class AlertListSerializer(CustomModelSerializer):
    """告警列表"""
    strategy_name = serializers.CharField(source='strategy.name', read_only=True, default='')

    class Meta:
        model = Alert
        fields = "__all__"


class AlertDetailSerializer(CustomModelSerializer):
    """告警详情 — 含日志"""
    logs = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = "__all__"

    def get_logs(self, obj):
        return AlertLogSerializer(obj.logs.all()[:50], many=True).data


class AlertAckSerializer(serializers.Serializer):
    """确认告警"""
    acknowledged_by = serializers.CharField(required=False, allow_blank=True)


class AlertAssignSerializer(serializers.Serializer):
    """转派告警"""
    assignee = serializers.CharField(required=True)


class AlertLogSerializer(CustomModelSerializer):
    class Meta:
        model = AlertLog
        fields = "__all__"


# ═══════════════════════════════════════════════════════════════════════
# 通知与值班
# ═══════════════════════════════════════════════════════════════════════

class DutyArrangeSerializer(CustomModelSerializer):
    class Meta:
        model = DutyArrange
        fields = "__all__"


class DutyPlanSerializer(CustomModelSerializer):
    arranges = DutyArrangeSerializer(many=True, read_only=True)

    class Meta:
        model = DutyPlan
        fields = "__all__"


class NotifyConfigSerializer(CustomModelSerializer):
    class Meta:
        model = NotifyConfig
        fields = "__all__"


class NotifyGroupSerializer(CustomModelSerializer):
    duty_plans = DutyPlanSerializer(many=True, read_only=True)
    notify_configs = NotifyConfigSerializer(many=True, read_only=True)

    class Meta:
        model = NotifyGroup
        fields = "__all__"


class NotifyGroupListSerializer(CustomModelSerializer):
    """通知组列表精简版"""
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = NotifyGroup
        fields = "__all__"

    def get_member_count(self, obj):
        return DutyArrange.objects.filter(plan__group=obj).values('user_id').distinct().count()


# ═══════════════════════════════════════════════════════════════════════
# 告警分派与动作
# ═══════════════════════════════════════════════════════════════════════

class AlertAssignRuleSerializer(CustomModelSerializer):
    class Meta:
        model = AlertAssignRule
        fields = "__all__"


class AlertAssignGroupSerializer(CustomModelSerializer):
    rules = AlertAssignRuleSerializer(many=True, read_only=True)

    class Meta:
        model = AlertAssignGroup
        fields = "__all__"


class ActionPluginSerializer(CustomModelSerializer):
    class Meta:
        model = ActionPlugin
        fields = "__all__"


# ═══════════════════════════════════════════════════════════════════════
# 屏蔽与采集
# ═══════════════════════════════════════════════════════════════════════

class ShieldPlanSerializer(CustomModelSerializer):
    class Meta:
        model = ShieldPlan
        fields = "__all__"


class CollectConfigSerializer(CustomModelSerializer):
    class Meta:
        model = CollectConfig
        fields = "__all__"
