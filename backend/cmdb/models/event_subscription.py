# -*- coding: utf-8 -*-
"""CMDB event subscription model — 实例变更事件的订阅配置"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class EventSubscription(CoreModel):
    """CMDB 事件订阅"""
    event_choices = (
        ('instance.create', '实例创建'),
        ('instance.update', '实例更新'),
        ('instance.delete', '实例删除'),
    )
    model_code = models.CharField(max_length=128, verbose_name="模型编码")
    event_type = models.CharField(max_length=64, choices=event_choices, verbose_name="事件类型")
    endpoint = models.CharField(max_length=512, verbose_name="回调地址")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    description = models.TextField(null=True, blank=True, verbose_name="描述")

    class Meta:
        db_table = table_prefix + "cmdb_event_subscription"
        verbose_name = "CMDB 事件订阅"
        verbose_name_plural = verbose_name
        unique_together = [['model_code', 'event_type', 'endpoint']]

    def __str__(self):
        return f"{self.model_code}.{self.event_type} → {self.endpoint}"
