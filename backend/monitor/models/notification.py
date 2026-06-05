# -*- coding: utf-8 -*-
"""Notification models — NotifyGroup, DutyPlan, DutyArrange, NotifyConfig

通知组管理 + 值班排班，参考 bk-monitor UserGroup / DutyPlan 设计。
"""

from django.db import models
from dvadmin.utils.models import table_prefix


class NotifyGroup(models.Model):
    """通知组 — 告警通知的接收者分组，可关联值班计划"""
    name = models.CharField(max_length=255, verbose_name="组名称")
    bk_biz_id = models.IntegerField(verbose_name="业务ID", db_index=True)
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")
    description = models.TextField(null=True, blank=True, verbose_name="描述")

    class Meta:
        db_table = table_prefix + "monitor_notify_group"
        verbose_name = "通知组"
        verbose_name_plural = verbose_name
        ordering = ["name"]

    def __str__(self):
        return self.name


class DutyPlan(models.Model):
    """值班计划 — 定义通知组的值班排班规则"""
    PLAN_TYPE_CHOICES = (
        ("daily", "每日"),
        ("weekly", "每周"),
        ("custom", "自定义"),
    )

    group = models.ForeignKey(
        NotifyGroup, on_delete=models.CASCADE,
        related_name="duty_plans", verbose_name="关联通知组",
    )
    name = models.CharField(max_length=255, verbose_name="计划名称")
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")
    plan_type = models.CharField(max_length=32, choices=PLAN_TYPE_CHOICES,
                                 default="daily", verbose_name="排班类型")
    config = models.JSONField(default=dict, verbose_name="排班配置",
                              help_text="按 plan_type 不同包含不同字段")

    class Meta:
        db_table = table_prefix + "monitor_duty_plan"
        verbose_name = "值班计划"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.group.name} / {self.name}"


class DutyArrange(models.Model):
    """排班明细 — 某人某时间段内值班"""
    DUTY_TYPE_CHOICES = (
        ("primary", "主值班"),
        ("backup", "备值班"),
    )

    plan = models.ForeignKey(
        DutyPlan, on_delete=models.CASCADE,
        related_name="arranges", verbose_name="关联值班计划",
    )
    user_id = models.IntegerField(verbose_name="值班人ID")
    user_name = models.CharField(max_length=128, verbose_name="值班人名称")
    date_from = models.DateTimeField(verbose_name="开始时间")
    date_to = models.DateTimeField(verbose_name="结束时间")
    duty_type = models.CharField(max_length=32, choices=DUTY_TYPE_CHOICES,
                                 default="primary", verbose_name="值班类型")

    class Meta:
        db_table = table_prefix + "monitor_duty_arrange"
        verbose_name = "排班明细"
        verbose_name_plural = verbose_name
        ordering = ["date_from"]

    def __str__(self):
        return f"{self.user_name} / {self.date_from.date()}"


class NotifyConfig(models.Model):
    """通知配置 — 通知组的通知渠道和通知时段"""
    CHANNEL_CHOICES = (
        ("wecom", "企业微信"),
        ("dingtalk", "钉钉"),
        ("email", "邮件"),
        ("sms", "短信"),
        ("webhook", "Webhook"),
    )

    group = models.ForeignKey(
        NotifyGroup, on_delete=models.CASCADE,
        related_name="notify_configs", verbose_name="关联通知组",
    )
    channel = models.CharField(max_length=64, choices=CHANNEL_CHOICES, verbose_name="通知通道")
    config = models.JSONField(default=dict, verbose_name="通道配置",
                              help_text="如 webhook_url、secret 等")
    notify_time = models.JSONField(default=dict, verbose_name="通知时段",
                                   help_text="如 {'start': '09:00', 'end': '18:00'}")
    at_mention = models.JSONField(default=list, verbose_name="@提及配置",
                                  help_text="如 ['user_id_1', 'group_id_1']")

    class Meta:
        db_table = table_prefix + "monitor_notify_config"
        verbose_name = "通知配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.group.name} / {self.get_channel_display()}"
