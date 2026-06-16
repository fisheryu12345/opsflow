# -*- coding: utf-8 -*-
"""AgentInstance model — Agent 注册表"""

import uuid

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


def generate_agent_id():
    return str(uuid.uuid4())


class AgentInstance(CoreModel):
    """Agent 实例 — 注册到平台的被管控主机 Agent"""

    status_choices = (
        ('online', '在线'),
        ('offline', '离线'),
        ('unknown', '未知'),
    )
    upgrade_status_choices = (
        ('none', '无'),
        ('upgrading', '升级中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('rollback', '已回滚'),
    )

    agent_id = models.CharField(
        max_length=64, unique=True, default=generate_agent_id,
        verbose_name="Agent ID", help_text="硬件指纹生成，唯一标识"
    )
    biz_id = models.IntegerField(null=True, blank=True, verbose_name="业务ID",
                                 help_text="对应 ops_project")
    hostname = models.CharField(max_length=255, blank=True, default='',
                                verbose_name="主机名")
    ip = models.CharField(max_length=64, blank=True, default='',
                          verbose_name="主 IP")
    ip_list = models.JSONField(default=list, verbose_name="IP 列表")
    os_type = models.CharField(max_length=32, blank=True, default='',
                               verbose_name="OS 类型",
                               help_text="linux / windows / aix")
    os_version = models.CharField(max_length=128, blank=True, default='',
                                  verbose_name="OS 版本")
    arch = models.CharField(max_length=32, blank=True, default='',
                            verbose_name="架构",
                            help_text="amd64 / arm64 / ppc64")
    agent_version = models.CharField(max_length=32, blank=True, default='',
                                     verbose_name="Agent 版本")
    status = models.CharField(max_length=32, choices=status_choices,
                              default='unknown', verbose_name="状态")
    last_heartbeat = models.DateTimeField(null=True, blank=True,
                                          verbose_name="最后心跳")
    first_register = models.DateTimeField(null=True, blank=True,
                                          verbose_name="首次注册")
    credential_token = models.CharField(max_length=128, blank=True, default='',
                                        verbose_name="凭证 Token(sha256)")
    tags = models.JSONField(default=dict, verbose_name="标签")
    enable_collect = models.BooleanField(default=True, verbose_name="开启采集")
    enable_file = models.BooleanField(default=True, verbose_name="开启文件传输")
    last_upgrade = models.DateTimeField(null=True, blank=True,
                                        verbose_name="最后升级时间")
    upgrade_status = models.CharField(
        max_length=32, choices=upgrade_status_choices,
        default='none', verbose_name="升级状态"
    )

    class Meta:
        db_table = table_prefix + "agent_instance"
        verbose_name = "Agent 实例"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.hostname or self.ip or self.agent_id}"
