# -*- coding: utf-8 -*-
"""Integration call audit log model

调用审计 — 记录所有通过集成中心发起的外部调用，用于排障和计量
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)


class IntegrationLog(CoreModel):
    """
    集成调用审计日志
    记录每一次通过集成中心发起的外部系统调用。
    """
    call_status_choices = (
        ('success', '成功'),
        ('failed', '失败'),
        ('timeout', '超时'),
        ('error', '异常'),
    )

    instance = models.ForeignKey(
        'ConnectorInstance', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='call_logs',
        verbose_name="连接器实例"
    )
    definition_code = models.CharField(max_length=128, null=True, blank=True,
                                       verbose_name="定义编码（快照）")
    action = models.CharField(max_length=255, verbose_name="操作",
                              help_text="如 describe_instances、send_sms")
    request_data = models.JSONField(default=dict, verbose_name="请求参数")
    response_data = models.JSONField(default=dict, verbose_name="返回数据")
    status = models.CharField(max_length=32, choices=call_status_choices,
                              default='success', verbose_name="调用状态")
    duration_ms = models.IntegerField(default=0, verbose_name="耗时(ms)")
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")
    source_app = models.CharField(max_length=128, null=True, blank=True,
                                  verbose_name="调用来源模块")
    ip_address = models.CharField(max_length=64, null=True, blank=True,
                                  verbose_name="请求 IP")

    class Meta:
        db_table = table_prefix + "intg_integration_log"
        verbose_name = "集成调用日志"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.instance} - {self.action} [{self.status}]"
