# -*- coding: utf-8 -*-
"""Admin configuration for Monitor app"""

from django.contrib import admin
from .models import (
    MonitorStrategy, MonitorItem, MonitorQueryConfig,
    MonitorDetectConfig, MonitorAlgorithmConfig,
    AlertEvent, Alert, AlertLog,
    NotifyGroup, DutyPlan, DutyArrange, NotifyConfig,
    AlertAssignGroup, AlertAssignRule, ActionPlugin,
    ShieldPlan, CollectConfig,
)


@admin.register(MonitorStrategy)
class MonitorStrategyAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'bk_biz_id', 'scenario', 'type', 'is_enabled', 'create_time']
    search_fields = ['name']
    list_filter = ['scenario', 'type', 'is_enabled']


@admin.register(MonitorItem)
class MonitorItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'strategy', 'metric_type']


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'event_id', 'alert_name', 'severity', 'status', 'time']
    list_filter = ['severity', 'status']


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['alert_id', 'title', 'severity', 'status', 'fired_at', 'event_count']
    list_filter = ['severity', 'status']


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = ['alert', 'operate', 'operator', 'create_time']
    list_filter = ['operate']


@admin.register(NotifyGroup)
class NotifyGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'bk_biz_id', 'is_enabled']


@admin.register(ActionPlugin)
class ActionPluginAdmin(admin.ModelAdmin):
    list_display = ['name', 'plugin_type', 'plugin_key', 'is_builtin']


@admin.register(ShieldPlan)
class ShieldPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'shield_type', 'is_enabled', 'bk_biz_id']


@admin.register(CollectConfig)
class CollectConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'data_source_label', 'is_enabled', 'interval']


admin.site.register(MonitorQueryConfig)
admin.site.register(MonitorDetectConfig)
admin.site.register(MonitorAlgorithmConfig)
admin.site.register(DutyPlan)
admin.site.register(DutyArrange)
admin.site.register(NotifyConfig)
admin.site.register(AlertAssignGroup)
admin.site.register(AlertAssignRule)
