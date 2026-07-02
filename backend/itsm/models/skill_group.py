from django.conf import settings
# -*- coding: utf-8 -*-
"""SkillGroup and OnDutySchedule models — IT 运维技能组与值班排班"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class SkillGroup(CoreModel):
    """技能组 — 如网络组、数据库组、应用组等"""
    business = models.ForeignKey(
        'iam.Business', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_skill_groups', verbose_name='Business',
    )
    name = models.CharField(max_length=128, verbose_name="技能组名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="技能组编码")
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='leading_groups', verbose_name="组长",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='skill_groups', verbose_name="组员",
    )
    description = models.TextField(blank=True, default='', verbose_name="说明")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "itsm_skill_group"
        verbose_name = "技能组"
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


class OnDutySchedule(CoreModel):
    """值班排班 — 每天每组的 primary/backup"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_schedules', verbose_name='Project',
    )
    DUTY_CHOICES = (
        ('primary', '主班'),
        ('backup', '备班'),
    )
    group = models.ForeignKey(
        SkillGroup, on_delete=models.CASCADE, related_name='duty_schedules',
        verbose_name="技能组",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='duty_schedules',
        verbose_name="值班人",
    )
    duty_date = models.DateField(verbose_name="值班日期")
    duty_type = models.CharField(max_length=16, choices=DUTY_CHOICES, default='primary',
                                  verbose_name="班型")

    class Meta:
        db_table = table_prefix + "itsm_on_duty_schedule"
        verbose_name = "值班排班"
        verbose_name_plural = verbose_name
        unique_together = [('group', 'duty_date', 'duty_type')]
        ordering = ['duty_date', 'group']

    def __str__(self):
        return f"{self.group.name}/{self.duty_date} {self.user.name}({self.get_duty_type_display()})"
