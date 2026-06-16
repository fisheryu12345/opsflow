# -*- coding: utf-8 -*-
"""AgentUpgrade model — Agent 升级记录"""

import uuid

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


def generate_uuid():
    return str(uuid.uuid4())


class AgentUpgrade(CoreModel):
    """Agent 升级记录"""

    status_choices = (
        ('pending', '等待中'),
        ('downloading', '下载中'),
        ('upgrading', '升级中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('rollback', '已回滚'),
    )

    upgrade_id = models.CharField(
        max_length=64, unique=True, default=generate_uuid, verbose_name="升级 ID"
    )
    agent = models.ForeignKey(
        'AgentInstance', on_delete=models.CASCADE,
        related_name='upgrades', verbose_name="目标 Agent"
    )
    from_version = models.CharField(max_length=32, verbose_name="旧版本")
    to_version = models.CharField(max_length=32, verbose_name="新版本")
    status = models.CharField(max_length=32, choices=status_choices,
                              default='pending', verbose_name="状态")
    checksum = models.CharField(max_length=128, blank=True, default='',
                                verbose_name="sha256")
    rollback_checksum = models.CharField(max_length=128, blank=True, default='',
                                         verbose_name="回滚版本 sha256")
    started_at = models.DateTimeField(null=True, blank=True,
                                      verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True,
                                       verbose_name="完成时间")
    error_msg = models.TextField(null=True, blank=True, verbose_name="错误信息")

    class Meta:
        db_table = table_prefix + "agent_upgrade"
        verbose_name = "Agent 升级记录"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']
