# -*- coding: utf-8 -*-
"""AssignRule model — 工单自动分派路由规则"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix
from itsm.models.skill_group import SkillGroup
from itsm.models.incident import ServiceCategory


class AssignRule(CoreModel):
    """分派规则 — IF category+priority+itsm_type THEN target_group+assign_mode"""
    ASSIGN_MODE_CHOICES = (
        ('to_group', '分派到组（待认领）'),
        ('to_onduty', '分派到当前值班人'),
        ('least_busy', '分派到待办最少的人'),
    )
    name = models.CharField(max_length=128, verbose_name="规则名称")
    priority = models.IntegerField(default=100, verbose_name="匹配优先级")
    match_category = models.ForeignKey(
        ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="匹配服务分类",
    )
    match_priority = models.CharField(
        max_length=8, null=True, blank=True, verbose_name="匹配优先级(P1-P4)",
    )
    match_itsm_type = models.CharField(
        max_length=32, null=True, blank=True, verbose_name="匹配工单类型(incident/change)",
    )
    target_group = models.ForeignKey(
        SkillGroup, on_delete=models.CASCADE, related_name='assign_rules',
        verbose_name="目标技能组",
    )
    assign_mode = models.CharField(
        max_length=32, choices=ASSIGN_MODE_CHOICES, default='to_onduty',
        verbose_name="分派模式",
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "itsm_assign_rule"
        verbose_name = "分派规则"
        verbose_name_plural = verbose_name
        ordering = ['priority']

    def __str__(self):
        return self.name
