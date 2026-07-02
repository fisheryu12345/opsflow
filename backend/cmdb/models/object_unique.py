# -*- coding: utf-8 -*-
"""ObjectUnique — 唯一约束，对标 bk-cmdb ObjectUnique

定义模型实例中一个或多个字段的组合值必须唯一。
约束在 Neo4j 中通过创建实例前的查询校验实现。
"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class ObjectUnique(CoreModel):
    """
    唯一约束 (ObjectUnique)
    对标 bk-cmdb ObjectUnique。
    keys 字段存储字段名列表，表示这些字段的组合值在实例中唯一。
    """
    model_definition = models.ForeignKey(
        'cmdb.ModelDefinition', on_delete=models.CASCADE,
        related_name='uniques',
        verbose_name="所属模型",
    )
    keys = models.JSONField(
        verbose_name="唯一字段列表",
        help_text='如 ["ip"] 或 ["hostname", "region"]',
    )
    is_pre = models.BooleanField(
        default=False,
        verbose_name="是否预置",
    )

    class Meta:
        db_table = table_prefix + "cmdb_object_unique"
        verbose_name = "唯一约束"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.model_definition.code}.unique({','.join(self.keys or [])})"
