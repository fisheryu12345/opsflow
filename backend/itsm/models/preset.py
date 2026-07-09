# -*- coding: utf-8 -*-
"""ITSM Preset model — reusable field value presets for workflow nodes and service items"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class Preset(CoreModel):
    """可复用的字段值预设"""
    TYPE_CHOICES = (
        ('user_list', '用户列表'),
        ('role_list', '角色列表'),
        ('dept_list', '部门列表'),
        ('text', '文本'),
        ('options', '选项列表'),
    )
    name = models.CharField(max_length=128, verbose_name="预设名称")
    preset_type = models.CharField(max_length=32, choices=TYPE_CHOICES, verbose_name="预设类型")
    value = models.JSONField(default=list, verbose_name="预设值")
    project = models.ForeignKey(
        'iam.Project', on_delete=models.PROTECT, null=True, blank=True,
        db_constraint=False, verbose_name="所属项目",
    )
    sort = models.IntegerField(default=1, verbose_name="排序")

    class Meta:
        db_table = table_prefix + "itsm_preset"
        verbose_name = "预设管理"
        verbose_name_plural = verbose_name
        ordering = ['sort', '-create_datetime']
        unique_together = [('name', 'project')]

    def __str__(self):
        return f"[{self.get_preset_type_display()}] {self.name}"
