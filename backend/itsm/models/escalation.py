from django.conf import settings
# -*- coding: utf-8 -*-
"""EscalationLevel model — 多级升级策略配置"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class EscalationLevel(CoreModel):
    """升级级别 — 每组可配置 L1→L2→L3 超时与动作"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_escalations', verbose_name='Project',
    )
    ACTION_CHOICES = (
        ('notify_only', '仅通知'),
        ('transfer_to_leader', '转给组长'),
        ('transfer_to_next_level', '升级到下一级'),
    )
    name = models.CharField(max_length=128, verbose_name="级别名称")
    level = models.IntegerField(verbose_name="升级顺序(1/2/3)")
    group = models.ForeignKey(
        'itsm.SkillGroup', on_delete=models.CASCADE, related_name='escalation_levels',
        verbose_name="所属技能组",
    )
    timeout_minutes = models.IntegerField(verbose_name="超时阈值(分钟)")
    action = models.CharField(
        max_length=32, choices=ACTION_CHOICES, default='transfer_to_next_level',
        verbose_name="超时动作",
    )
    notify_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='+', verbose_name="通知用户",
    )

    class Meta:
        db_table = table_prefix + "itsm_escalation_level"
        verbose_name = "升级级别"
        verbose_name_plural = verbose_name
        unique_together = [('group', 'level')]
        ordering = ['group', 'level']

    def __str__(self):
        return f"{self.group.name} / {self.name}"
