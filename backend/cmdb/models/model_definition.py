# -*- coding: utf-8 -*-
"""ModelDefinition & ModelField — 模型定义和字段，对标 bk-cmdb Object & Attribute

ModelDefinition.code → Neo4j Label
ModelField.name → Neo4j Property Key
"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


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


class ModelDefinition(CoreModel):
    """
    模型定义 (Model/Object)
    对标 bk-cmdb Object。code 作为 Neo4j Label 标识。
    内置模型 (is_builtin=True) 不可删除。
    """
    code = models.CharField(
        max_length=128, unique=True,
        verbose_name="模型编码",
        help_text="如 Biz、Host、Router — 也是 Neo4j Label 名称",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="模型名称",
        help_text="如 业务、主机、路由器",
    )
    classification = models.ForeignKey(
        'cmdb.Classification', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='models',
        verbose_name="所属分类",
    )
    business = models.ForeignKey(
        'iam.Business', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Business',
        help_text='Business line for tenant isolation / 业务线归属'
    )
    icon = models.CharField(
        max_length=128, null=True, blank=True,
        verbose_name="图标",
    )
    description = models.TextField(
        null=True, blank=True,
        verbose_name="描述",
    )
    is_builtin = models.BooleanField(
        default=False,
        verbose_name="是否内置",
        help_text="内置模型不可删除",
    )
    is_paused = models.BooleanField(
        default=False,
        verbose_name="是否暂停",
        help_text="暂停后不可创建新实例",
    )
    source = models.CharField(
        max_length=32,
        choices=[('builtin', '内置'), ('custom', '自定义')],
        default='custom',
        verbose_name="来源",
    )

    class Meta:
        db_table = table_prefix + "cmdb_model_definition"
        verbose_name = "模型定义"
        verbose_name_plural = verbose_name
        ordering = ['-is_builtin', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class ModelField(CoreModel):
    """
    模型字段定义 (Attribute)
    对标 bk-cmdb Attribute。定义模型实例的一个属性。
    """
    model_definition = models.ForeignKey(
        ModelDefinition, on_delete=models.CASCADE,
        related_name='fields',
        verbose_name="所属模型",
    )
    name = models.CharField(
        max_length=128,
        verbose_name="字段名",
        help_text="英文字段名，如 ip、cpu_cores — 也是 Neo4j 属性键",
    )
    label = models.CharField(
        max_length=255,
        verbose_name="显示名",
        help_text="如 IP 地址、CPU 核数",
    )
    field_type = models.CharField(
        max_length=32, choices=FIELD_TYPE_CHOICES,
        default='string',
        verbose_name="字段类型",
    )
    required = models.BooleanField(
        default=False,
        verbose_name="是否必填",
    )
    is_unique = models.BooleanField(
        default=False,
        verbose_name="是否唯一",
        help_text="该字段在模型实例中值唯一",
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name="是否系统字段",
        help_text="系统字段不可通过 API 直接修改",
    )
    is_readonly = models.BooleanField(
        default=False,
        verbose_name="是否只读",
    )
    default_value = models.JSONField(
        null=True, blank=True,
        verbose_name="默认值",
    )
    options = models.JSONField(
        null=True, blank=True,
        verbose_name="枚举选项",
        help_text="enum 类型时的可选值列表，如 ['生产','测试','开发']",
    )
    placeholder = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="占位提示",
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name="排序",
    )
    group = models.ForeignKey(
        'cmdb.AttributeGroup', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='fields',
        verbose_name="所属分组",
    )
    unit = models.CharField(
        max_length=64, null=True, blank=True,
        verbose_name="单位",
        help_text="如 MB、GB",
    )
    help_text = models.TextField(
        null=True, blank=True,
        verbose_name="帮助说明",
    )

    class Meta:
        db_table = table_prefix + "cmdb_model_field"
        verbose_name = "模型字段"
        verbose_name_plural = verbose_name
        ordering = ['model_definition', 'sort_order', 'name']
        unique_together = [['model_definition', 'name']]

    def __str__(self):
        return f"{self.model_definition.code}.{self.name}"
