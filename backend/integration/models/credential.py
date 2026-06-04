# -*- coding: utf-8 -*-
"""Credential model for Integration Hub

凭证管理 — 加密存储外部系统的访问凭据（AK/SK、密码、Token 等）
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)


class ConnectorCredential(CoreModel):
    """
    连接器凭证
    与连接器实例关联的敏感凭据，AES-256 加密存储。
    支持多种凭证类型：access_key / password / token / certificate。
    """
    cred_type_choices = (
        ('access_key', 'Access Key + Secret Key'),
        ('password', '密码'),
        ('token', 'Token'),
        ('certificate', '证书'),
        ('custom', '自定义'),
    )

    instance = models.ForeignKey(
        'ConnectorInstance', on_delete=models.CASCADE,
        related_name='credentials', verbose_name="所属实例"
    )
    name = models.CharField(max_length=255, verbose_name="凭证名称",
                            help_text="如 阿里云 AK、数据库密码")
    cred_type = models.CharField(max_length=64, choices=cred_type_choices,
                                 default='access_key', verbose_name="凭证类型")
    encrypted_value = models.TextField(verbose_name="加密后的凭证值",
                                       help_text="AES-256 加密存储")
    expire_at = models.DateTimeField(null=True, blank=True, verbose_name="过期时间")
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name="最后使用时间")
    remark = models.TextField(null=True, blank=True, verbose_name="备注")

    class Meta:
        db_table = table_prefix + "intg_connector_credential"
        verbose_name = "连接器凭证"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.name} ({self.get_cred_type_display()})"
