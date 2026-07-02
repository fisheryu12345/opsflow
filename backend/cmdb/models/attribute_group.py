# -*- coding: utf-8 -*-
"""AttributeGroup — 属性分组，对标 bk-cmdb AttributeGroup

用于前端展示时将字段分组显示，如"基本信息"、"硬件规格"、"网络配置"。
"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class AttributeGroup(CoreModel):
    """
    属性分组 (AttributeGroup)
    对标 bk-cmdb AttributeGroup，用于字段的分组展示。
    """
    model_definition = models.ForeignKey(
        'cmdb.ModelDefinition', on_delete=models.CASCADE,
        related_name='attr_groups',
        verbose_name="所属模型",
    )
    group_id = models.CharField(
        max_length=128,
        verbose_name="分组标识",
        help_text="内部标识，如 basic_info、hardware_spec",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="分组名称",
        help_text="显示名，如 基本信息、硬件规格",
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="排序",
    )

    class Meta:
        db_table = table_prefix + "cmdb_attribute_group"
        verbose_name = "属性分组"
        verbose_name_plural = verbose_name
        ordering = ['model_definition', 'sort_order']
        unique_together = [['model_definition', 'group_id']]

    def __str__(self):
        return f"{self.model_definition.code}.{self.name}"
