# -*- coding: utf-8 -*-
"""AgentTaskExecution model — 任务执行记录"""

import uuid

from django.db import models
from common.utils.models import CoreModel, table_prefix


def generate_uuid():
    return str(uuid.uuid4())


class AgentTaskExecution(CoreModel):
    """Agent 任务执行记录"""

    source_choices = (
        ('job_platform', '作业平台'),
        ('opsflow', '流程引擎'),
        ('opsagent', 'AI 助手'),
        ('open_api', '开放 API'),
        ('manual', '手动下发'),
    )
    status_choices = (
        ('pending', '等待中'),
        ('dispatching', '下发中'),
        ('running', '运行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('timeout', '超时'),
        ('cancelled', '取消'),
    )

    exec_id = models.CharField(
        max_length=64, unique=True, default=generate_uuid,
        verbose_name="执行 ID"
    )
    biz_id = models.IntegerField(null=True, blank=True, verbose_name="业务ID")
    task_source = models.CharField(max_length=32, choices=source_choices,
                                   default='manual', verbose_name="任务来源")
    source_id = models.CharField(max_length=128, blank=True, default='',
                                 verbose_name="来源方业务 ID")
    agent = models.ForeignKey(
        'AgentInstance', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tasks', verbose_name="目标 Agent"
    )
    target_host = models.CharField(max_length=255, blank=True, default='',
                                   verbose_name="目标主机")
    script_type = models.CharField(max_length=32, blank=True, default='shell',
                                   verbose_name="脚本类型",
                                   help_text="shell / bat / powershell / python")
    timeout = models.IntegerField(default=3600, verbose_name="超时秒数")
    status = models.CharField(max_length=32, choices=status_choices,
                              default='pending', verbose_name="状态")
    exit_code = models.IntegerField(null=True, blank=True, verbose_name="退出码")
    error_msg = models.TextField(null=True, blank=True, verbose_name="错误信息")
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finish_time = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    class Meta:
        db_table = table_prefix + "agent_task_execution"
        verbose_name = "Agent 任务执行"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.exec_id[:8]}... ({self.status})"
