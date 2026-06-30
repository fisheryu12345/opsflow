# -*- coding: utf-8 -*-
"""MainlineTopo — 主线拓扑定义，对标 bk-cmdb 主线概念

定义业务拓扑的层级关系链，如：Biz → Set → Module → Host。
每层通过 parent_model 指向父级模型，构成层次树。
"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


class MainlineTopo(CoreModel):
    """
    主线拓扑定义 (MainlineTopo)
    对标 bk-cmdb 主线概念。定义模型的拓扑层级关系。
    如 Biz → Set → Module → Host，每层通过 parent_model 关联。
    """
    model_definition = models.OneToOneField(
        'cmdb.ModelDefinition', on_delete=models.CASCADE,
        related_name='mainline_topo',
        verbose_name="模型",
    )
    parent_model = models.ForeignKey(
        'cmdb.ModelDefinition', on_delete=models.CASCADE,
        null=True, blank=True, related_name='children',
        verbose_name="父级模型",
        help_text="上一级模型，顶层模型（如 Biz）此字段为空",
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="层级顺序",
        help_text="从顶层到底层递增",
    )

    class Meta:
        db_table = table_prefix + "cmdb_mainline_topo"
        verbose_name = "主线拓扑"
        verbose_name_plural = verbose_name
        ordering = ['sort_order']

    def __str__(self):
        parent = self.parent_model.code if self.parent_model else "ROOT"
        return f"{parent} → {self.model_definition.code}"
