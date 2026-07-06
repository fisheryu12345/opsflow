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


class SlaPolicy(CoreModel):
    """SLA 策略定义"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_sla_policies', verbose_name='Project',
    )
    priority_choices = (
        ('P1', 'P1 危急'),
        ('P2', 'P2 高'),
        ('P3', 'P3 中'),
        ('P4', 'P4 低'),
    )
    name = models.CharField(max_length=128, verbose_name="策略名称")
    priority = models.CharField(max_length=8, choices=priority_choices, unique=True, verbose_name="优先级")
    response_minutes = models.IntegerField(default=60, verbose_name="响应时限(分钟)")
    resolve_minutes = models.IntegerField(default=480, verbose_name="解决时限(分钟)")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "itsm_sla_policy"
        verbose_name = "SLA 策略"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name} ({self.priority})"
