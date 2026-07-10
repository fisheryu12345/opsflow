# -*- coding: utf-8 -*-
"""Trigger models for event-driven ITSM automation."""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class Trigger(CoreModel):
    """触发器 — 工单事件 → 自动化动作映射"""

    EVENT_TYPE_CHOICES = (
        ('FLOW_START', '流程开始'),
        ('FLOW_END', '流程结束'),
        ('ENTER_STATE', '接入节点'),
        ('LEAVE_STATE', '离开节点'),
    )

    PRIORITY_CHOICES = (
        ('', '全部'),
        ('P1', 'P1 危急'),
        ('P2', 'P2 高'),
        ('P3', 'P3 中'),
        ('P4', 'P4 低'),
    )

    name = models.CharField(max_length=128, verbose_name="触发器名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="触发器名称(英文)")
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_triggers', verbose_name='Project',
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    event_type = models.CharField(max_length=16, choices=EVENT_TYPE_CHOICES, verbose_name="事件类型")
    workflow = models.ForeignKey(
        'itsm.Workflow', on_delete=models.CASCADE,
        related_name='triggers', verbose_name="流程模板",
    )
    states = models.ManyToManyField(
        'itsm.State', blank=True, related_name='triggers', verbose_name="适用节点",
        help_text="ENTER_STATE/LEAVE_STATE 时必须指定节点；FLOW_START/FLOW_END 时忽略",
    )
    priority = models.CharField(
        max_length=4, choices=PRIORITY_CHOICES, blank=True, default='',
        verbose_name="优先级过滤",
    )
    condition = models.JSONField(
        default=dict, blank=True, verbose_name="字段条件",
        help_text='{"logic":"AND","rules":[{"source":"ticket","field":"...","op":"==","value":"..."}]}',
    )

    class Meta:
        db_table = table_prefix + "itsm_trigger"
        verbose_name = "触发器"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def display_name(self, lang='zh'):
        return self.name_en if lang == 'en' and self.name_en else self.name


class TriggerAction(models.Model):
    """触发器动作 — 一条触发器可有多条动作，按 order 顺序执行"""

    ACTION_TYPE_CHOICES = (
        ('NOTIFY', '发送通知'),
        ('WEBHOOK', 'HTTP 回调'),
        ('OPSFLOW', '触发运维流程'),
        ('MODIFY_FIELD', '修改工单字段'),
    )

    trigger = models.ForeignKey(
        Trigger, on_delete=models.CASCADE, related_name='actions', verbose_name="触发器"
    )
    order = models.IntegerField(default=0, verbose_name="执行顺序")
    action_type = models.CharField(max_length=16, choices=ACTION_TYPE_CHOICES, verbose_name="动作类型")
    config = models.JSONField(default=dict, verbose_name="动作配置")

    class Meta:
        db_table = table_prefix + "itsm_trigger_action"
        verbose_name = "触发器动作"
        verbose_name_plural = verbose_name
        ordering = ['order']

    def __str__(self):
        return f"{self.trigger.name} / {self.get_action_type_display()}"


class TriggerExecution(models.Model):
    """触发器执行记录 — 异步执行日志，365 天自动清理"""

    STATUS_CHOICES = (
        ('PENDING', '等待执行'),
        ('PROCESSING', '执行中'),
        ('SUCCESS', '执行成功'),
        ('FAILED', '执行失败'),
    )

    trigger = models.ForeignKey(
        Trigger, on_delete=models.SET_NULL, null=True,
        related_name='executions', verbose_name="触发器",
    )
    ticket = models.ForeignKey(
        'itsm.Ticket', on_delete=models.CASCADE,
        related_name='trigger_executions', verbose_name="工单",
    )
    event_type = models.CharField(max_length=16, verbose_name="事件类型")
    status = models.CharField(
        max_length=8, choices=STATUS_CHOICES, default='PENDING', verbose_name="状态"
    )
    action_results = models.JSONField(default=list, verbose_name="动作执行结果")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = table_prefix + "itsm_trigger_execution"
        verbose_name = "触发器执行记录"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} → {self.status}"
