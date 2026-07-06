# -*- coding: utf-8 -*-
"""Escalation Level model — SLA 超时升级配置"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class EscalationLevel(CoreModel):
    """升级级别 — SLA 超时后的处理层级"""
    ACTION_CHOICES = (
        ('notify_only', '仅通知'),
        ('transfer_leader', '转给组长'),
        ('transfer_next', '升级到下一级'),
        ('notify_users', '通知用户'),
    )

    name = models.CharField(max_length=128, verbose_name="级别名称")
    level = models.IntegerField(default=1, verbose_name="级别序号")
    timeout_minutes = models.IntegerField(default=60, verbose_name="超时阈值(分钟)")
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, default='notify_only',
                              verbose_name="升级动作")
    notify_users = models.TextField(blank=True, default='', verbose_name="通知用户",
                                    help_text="action=notify_users 时的通知对象，逗号分隔")
    is_active = models.BooleanField(default=True, verbose_name="启用")

    class Meta:
        db_table = table_prefix + "itsm_escalation_level"
        verbose_name = "升级级别"
        verbose_name_plural = verbose_name
        ordering = ['level']

    def __str__(self):
        return f"L{self.level} {self.name} ({self.get_action_display()})"
