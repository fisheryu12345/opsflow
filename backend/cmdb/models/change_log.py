# -*- coding: utf-8 -*-
"""CMDB change log model — 记录模型实例的变更历史"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class ChangeLog(CoreModel):
    """CMDB 变更日志"""
    action_choices = (
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
    )
    model_code = models.CharField(max_length=128, verbose_name="模型编码")
    instance_id = models.CharField(max_length=64, verbose_name="实例 ID")
    action = models.CharField(max_length=32, choices=action_choices, verbose_name="操作")
    changes = models.JSONField(default=dict, verbose_name="变更详情")
    operator = models.CharField(max_length=128, null=True, blank=True, verbose_name="操作人")

    class Meta:
        db_table = table_prefix + "cmdb_change_log"
        verbose_name = "CMDB 变更日志"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"[{self.action}] {self.model_code}.{self.instance_id}"
