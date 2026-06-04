# -*- coding: utf-8 -*-
"""Monitor and alerting model definitions

告警规则、事件、通知策略、监控目标 — CoreModel 基类
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)


class AlertRule(CoreModel):
    """告警规则定义"""
    severity_choices = (
        ('critical', '严重'),
        ('warning', '警告'),
        ('info', '信息'),
    )
    status_choices = (
        ('enabled', '启用'),
        ('disabled', '禁用'),
    )

    name = models.CharField(max_length=255, verbose_name="规则名称")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    severity = models.CharField(max_length=32, choices=severity_choices, default='warning', verbose_name="严重级别")
    status = models.CharField(max_length=32, choices=status_choices, default='enabled', verbose_name="状态")
    condition_expr = models.TextField(verbose_name="告警条件表达式",
                                       help_text="如 cpu_usage > 90 持续 5 分钟")
    duration_seconds = models.IntegerField(default=300, verbose_name="持续时长(秒)")
    silence_seconds = models.IntegerField(default=3600, verbose_name="静默时长(秒)")
    auto_resolve_seconds = models.IntegerField(default=0, verbose_name="自动恢复时长(秒)", help_text="0 表示不自动恢复")
    notify_channels = models.JSONField(default=list, verbose_name="通知通道",
                                        help_text="通过集成中心的通知通道编码列表")
    notify_groups = models.JSONField(default=list, verbose_name="通知组",
                                      help_text="通知组 ID 列表")
    is_template = models.BooleanField(default=False, verbose_name="是否模板")
    source = models.CharField(max_length=64, default='prometheus', verbose_name="数据源类型",
                               help_text="prometheus / influxdb / grafana / manual")

    class Meta:
        db_table = table_prefix + "monitor_alert_rule"
        verbose_name = "告警规则"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return self.name


class AlertEvent(CoreModel):
    """告警事件 (Alert Event)"""
    status_choices = (
        ('firing', '触发中'),
        ('acknowledged', '已确认'),
        ('resolved', '已恢复'),
        ('silenced', '已静默'),
        ('closed', '已关闭'),
    )
    severity_choices = (
        ('critical', '严重'),
        ('warning', '警告'),
        ('info', '信息'),
    )

    alert_id = models.CharField(max_length=128, unique=True, verbose_name="告警 ID",
                                 help_text="Grafana/Prometheus 告警 ID")
    rule = models.ForeignKey(AlertRule, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='events', verbose_name="关联规则")
    title = models.CharField(max_length=255, verbose_name="标题")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    status = models.CharField(max_length=32, choices=status_choices, default='firing', verbose_name="状态")
    severity = models.CharField(max_length=32, choices=severity_choices, default='warning', verbose_name="严重级别")
    metric_value = models.FloatField(null=True, blank=True, verbose_name="指标值")
    metric_unit = models.CharField(max_length=64, null=True, blank=True, verbose_name="指标单位")
    labels = models.JSONField(default=dict, verbose_name="标签")
    annotations = models.JSONField(default=dict, verbose_name="注解")
    fired_at = models.DateTimeField(verbose_name="触发时间")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="恢复时间")
    acknowledged_at = models.DateTimeField(null=True, blank=True, verbose_name="确认时间")
    acknowledged_by = models.CharField(max_length=128, null=True, blank=True, verbose_name="确认人")

    # CMDB 关联
    cmdb_host_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="关联主机 ID")
    cmdb_biz_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="关联业务 ID")

    # ITSM 关联
    incident = models.ForeignKey('itsm.Incident', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='alerts', verbose_name="关联事件工单")

    class Meta:
        db_table = table_prefix + "monitor_alert_event"
        verbose_name = "告警事件"
        verbose_name_plural = verbose_name
        ordering = ['-fired_at']

    def __str__(self):
        return f"[{self.severity}] {self.title}"


class MonitorTarget(CoreModel):
    """监控目标 (Target)"""
    target_type_choices = (
        ('host', '主机'),
        ('service', '服务'),
        ('network', '网络设备'),
        ('middleware', '中间件'),
        ('custom', '自定义'),
    )

    name = models.CharField(max_length=255, verbose_name="目标名称")
    target_type = models.CharField(max_length=64, choices=target_type_choices, default='host', verbose_name="目标类型")
    endpoint = models.CharField(max_length=512, verbose_name="采集端点",
                                 help_text="如 http://192.168.1.1:9090/metrics")
    source = models.CharField(max_length=64, default='prometheus', verbose_name="数据源",
                               help_text="prometheus / influxdb / telegraf")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    cmdb_host_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="关联 CMDB 主机 ID")
    labels = models.JSONField(default=dict, verbose_name="标签")
    extra_config = models.JSONField(default=dict, verbose_name="额外配置")

    class Meta:
        db_table = table_prefix + "monitor_target"
        verbose_name = "监控目标"
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.source})"
