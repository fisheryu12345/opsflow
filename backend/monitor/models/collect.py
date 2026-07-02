# -*- coding: utf-8 -*-
"""CollectConfig model — 采集配置（数据源接入配置）"""

from django.db import models
from common.utils.models import table_prefix


class CollectConfig(models.Model):
    """采集配置 — 定义如何采集监控指标（Prometheus/InfluxDB/自建插件）"""
    name = models.CharField(max_length=255, verbose_name="配置名称")
    bk_biz_id = models.IntegerField(verbose_name="业务ID")
    data_source_label = models.CharField(max_length=32, verbose_name="数据源标签",
                                         help_text="prometheus / influxdb / custom")
    target = models.JSONField(default=dict, verbose_name="采集目标",
                              help_text="IP列表 / 服务发现配置")
    plugin = models.CharField(max_length=128, blank=True, default="", verbose_name="采集插件")
    config = models.JSONField(default=dict, verbose_name="采集参数",
                              help_text="如 port / path / metrics 配置")
    interval = models.IntegerField(default=60, verbose_name="采集周期(秒)")
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")
    create_user = models.CharField(max_length=128, blank=True, default="", verbose_name="创建人")

    class Meta:
        db_table = table_prefix + "monitor_collect_config"
        verbose_name = "采集配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
