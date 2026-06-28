# -*- coding: utf-8 -*-
"""Model definitions for Integration Hub

连接器定义与实例 — 管理外部系统的连接器注册和运行实例
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)


class ConnectorDefinition(CoreModel):
    """
    连接器定义
    描述一种连接器类型（如 阿里云ECS、企业微信、短信网关），
    包含其配置 JSON Schema 和实现类路径。
    """
    category_choices = (
        ('cloud', '云厂商'),
        ('notification', '通知通道'),
        ('auth', '认证源'),
        ('paas', 'PaaS 平台'),
        ('monitor', '监控系统'),
        ('ai', 'AI 服务'),
        ('other', '其他'),
    )

    code = models.CharField(max_length=128, unique=True, verbose_name="编码",
                            help_text="唯一编码，如 aliyun_ecs、wecom")
    name = models.CharField(max_length=255, verbose_name="名称",
                            help_text="展示名称，如 阿里云ECS、企业微信")
    category = models.CharField(max_length=64, choices=category_choices,
                                default='other', verbose_name="分类")
    version = models.CharField(max_length=32, default='1.0', verbose_name="版本")
    icon = models.CharField(max_length=512, null=True, blank=True, verbose_name="图标 URL")
    config_schema = models.JSONField(default=dict, verbose_name="配置 JSON Schema",
                                     help_text="定义实例配置字段的表单 schema")
    provider_class = models.CharField(max_length=512, null=True, blank=True,
                                      verbose_name="适配器类路径",
                                      help_text="如 integration.adapters.cloud.aliyun.AliyunConnector")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    sort_order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = table_prefix + "intg_connector_definition"
        verbose_name = "连接器定义"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class ConnectorInstance(CoreModel):
    """
    连接器实例
    连接器定义的一个具体实例，包含实际配置（不含敏感凭证）。
    例如 "生产环境阿里云"、"测试环境企业微信"。
    """
    status_choices = (
        ('online', '在线'),
        ('offline', '离线'),
        ('error', '异常'),
        ('unknown', '未知'),
    )

    definition = models.ForeignKey(
        ConnectorDefinition, on_delete=models.CASCADE,
        related_name='instances', verbose_name="所属定义"
    )
    business = models.ForeignKey(
        'iam.Business', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Business',
        help_text='Business line for tenant isolation / 业务线归属'
    )
    name = models.CharField(max_length=255, verbose_name="实例名称",
                            help_text="如 生产环境阿里云、测试环境企微")
    config = models.JSONField(default=dict, verbose_name="配置（非敏感）",
                              help_text="region、endpoint 等非敏感配置项")
    status = models.CharField(max_length=32, choices=status_choices,
                              default='unknown', verbose_name="状态")
    health_check_url = models.CharField(max_length=512, null=True, blank=True,
                                        verbose_name="健康检查地址")
    last_health_check = models.DateTimeField(null=True, blank=True,
                                             verbose_name="最后健康检查时间")
    last_health_message = models.TextField(null=True, blank=True,
                                           verbose_name="健康检查消息")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "intg_connector_instance"
        verbose_name = "连接器实例"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.name} ({self.definition.code})"
