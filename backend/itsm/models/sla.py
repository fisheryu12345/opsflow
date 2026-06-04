# -*- coding: utf-8 -*-
"""ITSM SLA model — SLA 策略、优先级矩阵、计时任务"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


class PriorityMatrix(CoreModel):
    """优先级矩阵 — 紧急程度 × 影响范围 → 优先级"""
    itsm_type = models.CharField(max_length=32, verbose_name="服务类型")
    urgency = models.CharField(max_length=16, verbose_name="紧急程度")
    impact = models.CharField(max_length=16, verbose_name="影响范围")
    priority = models.CharField(max_length=16, verbose_name="优先级")

    class Meta:
        db_table = table_prefix + "itsm_priority_matrix"
        verbose_name = "优先级矩阵"
        verbose_name_plural = verbose_name
        unique_together = [('itsm_type', 'urgency', 'impact')]

    def __str__(self):
        return f"{self.itsm_type} {self.urgency}x{self.impact} → {self.priority}"


class SlaTask(CoreModel):
    """SLA 计时任务 — 工单级别的计时"""
    TASK_STATUS = (
        ('unactivated', '未激活'),
        ('running', '运行中'),
        ('paused', '已暂停'),
        ('stopped', '已停止'),
    )
    SLA_STATUS = (
        ('normal', '正常'),
        ('warning', '即将超时'),
        ('violated', '已超时'),
    )
    ticket = models.ForeignKey('itsm.Ticket', on_delete=models.CASCADE,
                               related_name='sla_tasks', verbose_name="工单")
    sla_policy = models.ForeignKey('itsm.SlaPolicy', on_delete=models.SET_NULL,
                                   null=True, verbose_name="SLA 策略")
    priority = models.CharField(max_length=16, verbose_name="当前优先级")
    deadline = models.DateTimeField(verbose_name="处理截止时间")
    reply_deadline = models.DateTimeField(null=True, blank=True, verbose_name="响应截止时间")
    cost_seconds = models.IntegerField(default=0, verbose_name="已用时间(秒)")
    task_status = models.CharField(max_length=16, choices=TASK_STATUS, default='unactivated',
                                    verbose_name="任务状态")
    sla_status = models.CharField(max_length=16, choices=SLA_STATUS, default='normal',
                                   verbose_name="SLA 状态")

    class Meta:
        db_table = table_prefix + "itsm_sla_task"
        verbose_name = "SLA 计时任务"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"SLA {self.ticket.sn} [{self.get_sla_status_display()}]"
