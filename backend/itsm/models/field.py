# -*- coding: utf-8 -*-
"""ITSM Field model — 节点表单字段定义"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


class Field(CoreModel):
    """表单字段定义 — 绑定到 State"""
    TYPE_CHOICES = (
        ('STRING', '单行文本'),
        ('TEXT', '多行文本'),
        ('INT', '数字'),
        ('DATE', '日期'),
        ('DATETIME', '日期时间'),
        ('SELECT', '下拉框'),
        ('RADIO', '单选框'),
        ('CHECKBOX', '多选框'),
        ('MULTISELECT', '多选下拉'),
        ('MEMBERS', '人员选择'),
        ('TABLE', '子表格'),
        ('FILE', '附件'),
        ('RICHTEXT', '富文本'),
        ('TREESELECT', '树形选择'),
        ('CASCADE', '级联选择'),
    )
    SOURCE_CHOICES = (
        ('CUSTOM', '自定义'),
        ('API', 'API 数据源'),
    )
    LAYOUT_CHOICES = (
        ('COL_12', '整行'),
        ('COL_8', '2/3'),
        ('COL_6', '半行'),
        ('COL_4', '1/3'),
        ('COL_3', '1/4'),
    )
    VALIDATE_CHOICES = (
        ('optional', '可选'),
        ('required', '必填'),
    )
    state = models.ForeignKey('itsm.State', on_delete=models.CASCADE,
                              related_name='field_defs', verbose_name="所属节点")
    key = models.CharField(max_length=64, verbose_name="字段标识")
    name = models.CharField(max_length=128, verbose_name="显示名称")
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, verbose_name="字段类型")
    required = models.BooleanField(default=False, verbose_name="是否必填")
    layout = models.CharField(max_length=16, choices=LAYOUT_CHOICES, default='COL_12',
                               verbose_name="布局")
    choice = models.JSONField(default=list, verbose_name="选项列表")
    default = models.JSONField(default=list, verbose_name="默认值")
    validate_type = models.CharField(max_length=16, choices=VALIDATE_CHOICES,
                                      default='optional', verbose_name="校验方式")
    show_conditions = models.JSONField(default=dict, verbose_name="显示条件")
    source_type = models.CharField(max_length=16, choices=SOURCE_CHOICES,
                                    default='CUSTOM', verbose_name="数据来源")
    meta = models.JSONField(default=dict, verbose_name="扩展元数据")
    sort_order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = table_prefix + "itsm_workflow_field"
        verbose_name = "表单字段"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.name} ({self.key})"
