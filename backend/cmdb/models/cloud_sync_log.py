# -*- coding: utf-8 -*-
"""CloudSyncLog — 云资产同步日志"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


class CloudSyncLog(CoreModel):
    """云厂商资产同步执行记录"""
    provider_choices = (
        ('aliyun', '阿里云'),
        ('aws', 'AWS'),
        ('tencent', '腾讯云'),
    )
    status_choices = (
        ('running', '同步中'),
        ('success', '同步成功'),
        ('failed', '同步失败'),
    )
    trigger_choices = (
        ('schedule', '定时任务'),
        ('manual', '手动触发'),
        ('pipeline', 'Pipeline 触发'),
    )

    provider = models.CharField(max_length=32, choices=provider_choices, verbose_name="云厂商")
    status = models.CharField(max_length=16, choices=status_choices, default='running', verbose_name="状态")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    total = models.IntegerField(default=0, verbose_name="总资产数")
    created_count = models.IntegerField(default=0, verbose_name="新增数")
    updated_count = models.IntegerField(default=0, verbose_name="更新数")
    error_count = models.IntegerField(default=0, verbose_name="错误数")
    errors = models.JSONField(default=list, blank=True, verbose_name="错误详情")
    details = models.TextField(default='', blank=True, verbose_name="同步详情")
    triggered_by = models.CharField(max_length=32, choices=trigger_choices, default='schedule', verbose_name="触发方式")

    class Meta:
        db_table = table_prefix + "cmdb_cloud_sync_log"
        verbose_name = "云同步日志"
        verbose_name_plural = verbose_name
        ordering = ['-started_at']

    def __str__(self):
        return f"[{self.provider}] {self.status} @ {self.started_at:%Y-%m-%d %H:%M}"
