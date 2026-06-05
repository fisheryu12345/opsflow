# -*- coding: utf-8 -*-
"""Action models — AlertAssignGroup, AlertAssignRule, ActionPlugin

告警分派规则与动作插件管理，参考 bk-monitor AlertAssignGroup / ActionPlugin 设计。
"""

from django.db import models
from dvadmin.utils.models import table_prefix


class AlertAssignGroup(models.Model):
    """告警分派规则组 — 按优先级排序的一组分派规则"""
    priority = models.IntegerField(default=-1, verbose_name="优先级", db_index=True)
    name = models.CharField(max_length=128, verbose_name="规则组名")
    bk_biz_id = models.IntegerField(default=0, blank=True, verbose_name="业务ID", db_index=True)
    is_builtin = models.BooleanField(default=False, verbose_name="是否内置")
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")
    settings = models.JSONField(default=dict, verbose_name="其他属性")

    class Meta:
        db_table = table_prefix + "monitor_assign_group"
        verbose_name = "告警分派规则组"
        verbose_name_plural = verbose_name
        ordering = ["priority"]

    def __str__(self):
        return f"{self.name} (P{self.priority})"


class AlertAssignRule(models.Model):
    """告警分派规则 — conditions 匹配则执行 action"""
    ACTION_TYPE_CHOICES = (
        ("notify", "通知"),
        ("webhook", "HTTP回调"),
        ("opsflow", "OpsFlow流程"),
        ("awx", "AWX作业"),
        ("itsm", "ITSM工单"),
    )

    assign_group = models.ForeignKey(
        AlertAssignGroup, on_delete=models.CASCADE,
        related_name="rules", verbose_name="关联规则组",
    )
    bk_biz_id = models.IntegerField(default=0, verbose_name="业务ID")
    name = models.CharField(max_length=128, verbose_name="规则名称")
    conditions = models.JSONField(default=dict, verbose_name="条件表达式",
                                  help_text="如 {'severity': [1,2], 'labels': {'key': 'value'}}")
    action_type = models.CharField(max_length=32, choices=ACTION_TYPE_CHOICES,
                                   default="notify", verbose_name="动作类型")
    notify_group = models.ForeignKey(
        "NotifyGroup", on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="通知组",
    )
    action_plugin = models.ForeignKey(
        "ActionPlugin", on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="动作插件",
    )
    action_config = models.JSONField(default=dict, verbose_name="动作配置")
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "monitor_assign_rule"
        verbose_name = "告警分派规则"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ActionPlugin(models.Model):
    """动作插件 — 告警触发后可执行的动作类型，支持插件化注册"""
    PLUGIN_TYPE_CHOICES = (
        ("notice", "通知"),
        ("webhook", "HTTP回调"),
        ("job", "作业平台"),
        ("sops", "标准运维"),
        ("itsm", "流程服务"),
        ("common", "通用插件"),
    )
    PLUGIN_SOURCE_CHOICES = (
        ("builtin", "内置"),
        ("peripheral", "周边系统"),
        ("bk_plugin", "蓝鲸插件"),
    )

    plugin_type = models.CharField(max_length=64, choices=PLUGIN_TYPE_CHOICES,
                                   verbose_name="插件类型")
    plugin_key = models.CharField(max_length=64, unique=True, verbose_name="插件唯一标识")
    name = models.CharField(max_length=64, verbose_name="插件名称")
    description = models.TextField(blank=True, default="", verbose_name="详细描述")
    is_builtin = models.BooleanField(default=False, verbose_name="是否内置")
    plugin_source = models.CharField(max_length=64, choices=PLUGIN_SOURCE_CHOICES,
                                     default="builtin", verbose_name="插件来源")
    has_child = models.BooleanField(default=False, verbose_name="是否有子级联")
    category = models.CharField(max_length=64, verbose_name="插件分类")
    config_schema = models.JSONField(default=dict, verbose_name="参数配置JSON Schema")
    adapter_class = models.CharField(max_length=512, null=True, blank=True,
                                     verbose_name="适配器类路径")

    class Meta:
        db_table = table_prefix + "monitor_action_plugin"
        verbose_name = "动作插件"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
