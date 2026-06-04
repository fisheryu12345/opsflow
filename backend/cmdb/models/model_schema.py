# -*- coding: utf-8 -*-
"""MySQL model definitions for CMDB schema management

存储自定义模型/字段的定义 schema，Neo4j 存节点实例
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)

# ─── 字段类型常量 ───
FIELD_TYPE_CHOICES = (
    ('string', '字符串'),
    ('integer', '整数'),
    ('float', '浮点数'),
    ('boolean', '布尔'),
    ('date', '日期'),
    ('datetime', '日期时间'),
    ('enum', '枚举'),
    ('json', 'JSON'),
    ('ip', 'IP 地址'),
)

CATEGORY_CHOICES = (
    ('business', '业务'),
    ('cluster', '集群'),
    ('module', '模块'),
    ('host', '主机'),
    ('process', '进程'),
    ('custom', '自定义'),
)


class ModelDefinition(CoreModel):
    """
    模型定义
    描述 CMDB 中的一种对象类型（如 业务、集群、主机），
    对应的 Neo4j Label 由 code 生成。
    """
    code = models.CharField(max_length=128, unique=True, verbose_name="模型编码",
                            help_text="如 biz、host、custom_router")
    name = models.CharField(max_length=255, verbose_name="模型名称",
                            help_text="如 业务、主机、自定义路由器")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    icon = models.CharField(max_length=128, null=True, blank=True, verbose_name="图标")
    category = models.CharField(max_length=64, choices=CATEGORY_CHOICES,
                                default='custom', verbose_name="分类")
    is_builtin = models.BooleanField(default=False, verbose_name="是否内置",
                                     help_text="内置模型不可删除")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "cmdb_model_definition"
        verbose_name = "模型定义"
        verbose_name_plural = verbose_name
        ordering = ['-is_builtin', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class ModelField(CoreModel):
    """
    模型字段定义
    描述模型的一个属性字段，如 Host 的 IP、CPU 核数。
    """
    model_definition = models.ForeignKey(
        ModelDefinition, on_delete=models.CASCADE,
        related_name='fields', verbose_name="所属模型"
    )
    name = models.CharField(max_length=128, verbose_name="字段名",
                            help_text="英文字段名，如 ip、cpu_cores")
    label = models.CharField(max_length=255, verbose_name="显示名",
                             help_text="如 IP 地址、CPU 核数")
    field_type = models.CharField(max_length=32, choices=FIELD_TYPE_CHOICES,
                                  default='string', verbose_name="字段类型")
    required = models.BooleanField(default=False, verbose_name="是否必填")
    default_value = models.JSONField(null=True, blank=True, verbose_name="默认值")
    options = models.JSONField(null=True, blank=True, verbose_name="枚举选项",
                               help_text="enum 类型时的可选值列表")
    placeholder = models.CharField(max_length=512, null=True, blank=True,
                                   verbose_name="占位提示")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_unique = models.BooleanField(default=False, verbose_name="是否唯一")
    help_text = models.TextField(null=True, blank=True, verbose_name="帮助说明")

    class Meta:
        db_table = table_prefix + "cmdb_model_field"
        verbose_name = "模型字段"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'name']
        unique_together = [['model_definition', 'name']]

    def __str__(self):
        return f"{self.model_definition.name}.{self.name}"
