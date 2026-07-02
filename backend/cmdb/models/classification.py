# -*- coding: utf-8 -*-
"""Classification model — 模型分类，对标 bk-cmdb Classification

模型分类用于对 CMDB 模型进行分组归类，如主机管理、业务拓扑、网络设备等。
"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class Classification(CoreModel):
    """
    模型分类 (Classification)
    对标 bk-cmdb Classification，用于对模型进行分组归类。
    """
    cls_id = models.CharField(
        max_length=128, unique=True,
        verbose_name="分类标识",
        help_text="如 bk_host_manage、bk_biz_topo",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="分类名称",
        help_text="如 主机管理、业务拓扑",
    )
    icon = models.CharField(
        max_length=128, null=True, blank=True,
        verbose_name="图标",
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="排序",
    )

    class Meta:
        db_table = table_prefix + "cmdb_classification"
        verbose_name = "模型分类"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.cls_id})"
