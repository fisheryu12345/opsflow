# -*- coding: utf-8 -*-
"""ServiceCategory and SlaPolicy — still actively used by Service Catalog and SLA engine"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class ServiceCategory(CoreModel):
    """服务分类 — 服务目录的一级/二级分类"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_categories', verbose_name='Project',
    )
    name = models.CharField(max_length=128, verbose_name="分类名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="分类名称(英文)")
    code = models.CharField(max_length=64, unique=True, verbose_name="分类编码")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                related_name='children', verbose_name="上级分类")
    icon = models.CharField(max_length=128, null=True, blank=True, verbose_name="图标")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "itsm_service_category"
        verbose_name = "服务分类"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def display_name(self, lang='zh'):
        return self.name_en if lang == 'en' and self.name_en else self.name


class SlaPolicy(CoreModel):
    """SLA 策略定义 — binds a Schedule (working time model) to a priority level."""
    TIME_UNIT_CHOICES = (
        ('m', '分钟'),
        ('h', '小时'),
        ('d', '天'),
    )
    priority_choices = (
        ('P1', 'P1 危急'),
        ('P2', 'P2 高'),
        ('P3', 'P3 中'),
        ('P4', 'P4 低'),
    )
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_sla_policies', verbose_name='Project',
    )
    name = models.CharField(max_length=128, verbose_name="策略名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="策略名称(英文)")
    priority = models.CharField(max_length=8, choices=priority_choices, verbose_name="优先级")
    schedule = models.ForeignKey(
        'itsm.Schedule', on_delete=models.PROTECT, verbose_name="排班表",
        help_text="Working schedule for working-time-aware SLA calculation.",
    )
    response_time = models.IntegerField(default=60, verbose_name="响应时限数值")
    response_unit = models.CharField(max_length=4, choices=TIME_UNIT_CHOICES, default='m',
                                      verbose_name="响应时限单位")
    resolve_time = models.IntegerField(default=480, verbose_name="解决时限数值")
    resolve_unit = models.CharField(max_length=4, choices=TIME_UNIT_CHOICES, default='m',
                                     verbose_name="解决时限单位")
    escalation_levels = models.ManyToManyField(
        'itsm.EscalationLevel', blank=True, verbose_name="升级级别",
        help_text="Ordered escalation actions when SLA is violated.",
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "itsm_sla_policy"
        verbose_name = "SLA 策略"
        verbose_name_plural = verbose_name
        unique_together = ('priority', 'schedule', 'project')

    def __str__(self):
        return f"{self.name} ({self.priority})"

    def display_name(self, lang='zh'):
        return self.name_en if lang == 'en' and self.name_en else self.name

    @property
    def response_seconds(self):
        """Convert response_time + response_unit to total seconds."""
        multipliers = {'m': 60, 'h': 3600, 'd': 86400}
        return self.response_time * multipliers.get(self.response_unit, 60)

    @property
    def resolve_seconds(self):
        """Convert resolve_time + resolve_unit to total seconds."""
        multipliers = {'m': 60, 'h': 3600, 'd': 86400}
        return self.resolve_time * multipliers.get(self.resolve_unit, 60)
