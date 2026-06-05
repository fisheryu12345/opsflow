# -*- coding: utf-8 -*-
"""Alert models — AlertEvent(原始事件), Alert(聚合告警), AlertLog(流水日志)

Event 与 Alert 分离设计，原始事件用于审计回溯，Alert 是收敛后可操作的告警实体。
"""

import hashlib
import json
from datetime import datetime

from django.db import models
from dvadmin.utils.models import table_prefix


# ═══════════════════════════════════════════════════════════════════════
# 原始告警事件 (AlertEvent)
# ═══════════════════════════════════════════════════════════════════════
class AlertEvent(models.Model):
    """
    原始告警事件 (Event)
    来自数据源 (Prometheus/Grafana/自建采集) 的原始告警记录。
    每条 event 对应一次检测触发，经策略匹配后可能创建/更新 Alert。
    """

    STATUS_CHOICES = (
        ("pending", "待处理"),
        ("abnormal", "异常"),
        ("recovered", "已恢复"),
        ("closed", "已关闭"),
    )

    SEVERITY_CHOICES = (
        (1, "致命"),
        (2, "预警"),
        (3, "提醒"),
    )

    # ── 标识 ──
    id = models.BigAutoField(primary_key=True)
    event_id = models.CharField(max_length=128, unique=True, verbose_name="事件ID",
                                 help_text="由数据源提供的唯一事件标识")
    strategy = models.ForeignKey(
        "MonitorStrategy", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="events",
        verbose_name="关联策略",
    )
    item = models.ForeignKey(
        "MonitorItem", on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="关联监控项",
    )

    # ── 内容 ──
    alert_name = models.CharField(max_length=255, verbose_name="告警名称")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    severity = models.IntegerField(choices=SEVERITY_CHOICES, default=3, verbose_name="级别")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES,
                              default="pending", verbose_name="状态", db_index=True)

    # ── 指标 ──
    target_type = models.CharField(max_length=64, default="host", verbose_name="目标类型",
                                   help_text="host / service / instance")
    target = models.CharField(max_length=512, verbose_name="目标标识",
                              help_text="如 IP / 服务名 / 实例ID")
    metric = models.CharField(max_length=128, blank=True, default="", verbose_name="指标名")
    metric_value = models.FloatField(null=True, blank=True, verbose_name="指标值")
    tags = models.JSONField(default=dict, verbose_name="标签")

    # ── 去重 ──
    dedupe_keys = models.JSONField(default=list, verbose_name="去重键列表")
    dedupe_md5 = models.CharField(max_length=64, verbose_name="去重指纹", db_index=True)

    # ── 时间 ──
    time = models.DateTimeField(verbose_name="事件时间")
    anomaly_time = models.DateTimeField(null=True, blank=True, verbose_name="异常时间")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="记录时间")

    # ── CMDB 关联 ──
    bk_biz_id = models.IntegerField(default=0, verbose_name="业务ID", db_index=True)
    cmdb_host_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="主机ID")
    cmdb_biz_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="业务ID")

    # ── 扩展 ──
    extra_info = models.JSONField(default=dict, verbose_name="扩展信息",
                                  help_text="数据源原始告警信息")

    class Meta:
        db_table = table_prefix + "monitor_alert_event"
        verbose_name = "原始告警事件"
        verbose_name_plural = verbose_name
        ordering = ["-time"]
        index_together = [("strategy", "status", "time")]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.alert_name}"


# ═══════════════════════════════════════════════════════════════════════
# 聚合告警 (Alert)
# ═══════════════════════════════════════════════════════════════════════
class Alert(models.Model):
    """
    聚合告警 (Alert)
    经过策略匹配、收敛后的可操作告警实体。
    一条 Alert 可关联 N 条原始 Event。
    """

    STATUS_CHOICES = (
        ("firing", "触发中"),
        ("acknowledged", "已确认"),
        ("resolved", "已恢复"),
        ("silenced", "已静默"),
        ("closed", "已关闭"),
    )
    SEVERITY_CHOICES = AlertEvent.SEVERITY_CHOICES

    id = models.BigAutoField(primary_key=True)
    alert_id = models.CharField(max_length=64, unique=True, verbose_name="告警ID",
                                 help_text="系统生成的唯一告警标识")
    strategy = models.ForeignKey(
        "MonitorStrategy", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="alerts",
        verbose_name="关联策略",
    )

    # ── 内容 ──
    severity = models.IntegerField(choices=SEVERITY_CHOICES, verbose_name="级别", db_index=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES,
                              default="firing", verbose_name="状态", db_index=True)
    title = models.CharField(max_length=255, verbose_name="告警标题")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    current_value = models.FloatField(null=True, blank=True, verbose_name="当前指标值")
    metric_unit = models.CharField(max_length=64, null=True, blank=True, verbose_name="指标单位")
    labels = models.JSONField(default=dict, verbose_name="标签")
    annotations = models.JSONField(default=dict, verbose_name="注解")

    # ── 时间 ──
    fired_at = models.DateTimeField(verbose_name="首次触发时间", db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="恢复时间")
    acknowledged_at = models.DateTimeField(null=True, blank=True, verbose_name="确认时间")
    acknowledged_by = models.CharField(max_length=128, null=True, blank=True, verbose_name="确认人")
    duration = models.IntegerField(default=0, verbose_name="持续时长(秒)")

    # ── 统计 ──
    event_count = models.IntegerField(default=1, verbose_name="累计事件数")

    # ── CMDB 关联 ──
    cmdb_host_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="主机ID")
    cmdb_biz_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="业务ID")

    # ── 分派与动作 ──
    assignee = models.CharField(max_length=128, null=True, blank=True, verbose_name="当前负责人")
    incident_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="关联工单ID")

    # ── 升级 ──
    escalation_count = models.IntegerField(default=0, verbose_name="升级次数")
    next_escalate_at = models.DateTimeField(null=True, blank=True, verbose_name="下次升级时间")

    class Meta:
        db_table = table_prefix + "monitor_alert"
        verbose_name = "聚合告警"
        verbose_name_plural = verbose_name
        ordering = ["-fired_at"]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"

    def generate_alert_id(self):
        """生成唯一告警ID"""
        raw = f"{self.strategy_id or ''}-{self.cmdb_host_id or ''}-{self.title}-{self.fired_at}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════
# 告警流水日志 (AlertLog)
# ═══════════════════════════════════════════════════════════════════════
class AlertLog(models.Model):
    """告警流水日志 — 记录告警生命周期中的所有状态变更和操作"""

    OPERATE_CHOICES = (
        ("created", "创建"),
        ("acknowledged", "确认"),
        ("resolved", "恢复"),
        ("closed", "关闭"),
        ("escalated", "升级"),
        ("silenced", "静默"),
        ("assigned", "分派"),
        ("notified", "通知"),
        ("action_executed", "动作执行"),
        ("incident_created", "创建工单"),
        ("updated", "更新"),
    )

    alert = models.ForeignKey(
        Alert, on_delete=models.CASCADE,
        related_name="logs", verbose_name="关联告警",
    )
    operate = models.CharField(max_length=32, choices=OPERATE_CHOICES, verbose_name="操作类型")
    operator = models.CharField(max_length=128, verbose_name="操作人/系统")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")
    description = models.TextField(verbose_name="操作描述")
    extra = models.JSONField(default=dict, verbose_name="变更详情")

    class Meta:
        db_table = table_prefix + "monitor_alert_log"
        verbose_name = "告警流水日志"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    def __str__(self):
        return f"{self.operate} @ {self.create_time}"
