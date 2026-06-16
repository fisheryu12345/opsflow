# -*- coding: utf-8 -*-
"""AgentFileTask model — 文件传输任务"""

import uuid

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


def generate_uuid():
    return str(uuid.uuid4())


class AgentFileTask(CoreModel):
    """Agent 文件传输任务"""

    direction_choices = (
        ('push', '推送 (控制台→主机)'),
        ('pull', '拉取 (主机→控制台)'),
    )
    status_choices = (
        ('pending', '等待中'),
        ('transferring', '传输中'),
        ('success', '成功'),
        ('failed', '失败'),
    )

    file_task_id = models.CharField(
        max_length=64, unique=True, default=generate_uuid,
        verbose_name="文件任务 ID"
    )
    biz_id = models.IntegerField(null=True, blank=True, verbose_name="业务ID")
    direction = models.CharField(max_length=16, choices=direction_choices,
                                 verbose_name="方向")
    source_type = models.CharField(max_length=16, blank=True, default='local',
                                   verbose_name="源类型")
    target_type = models.CharField(max_length=16, blank=True, default='agent',
                                   verbose_name="目标类型")
    file_name = models.CharField(max_length=512, verbose_name="文件名")
    file_size = models.BigIntegerField(default=0, verbose_name="文件大小")
    file_hash = models.CharField(max_length=128, blank=True, default='',
                                 verbose_name="文件 sha256")
    chunk_size = models.IntegerField(default=4194304, verbose_name="分块大小")
    status = models.CharField(max_length=32, choices=status_choices,
                              default='pending', verbose_name="状态")
    progress = models.IntegerField(default=0, verbose_name="进度 0-100")
    error_msg = models.TextField(null=True, blank=True, verbose_name="错误信息")

    class Meta:
        db_table = table_prefix + "agent_file_task"
        verbose_name = "Agent 文件传输"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']
