# -*- coding: utf-8 -*-
"""AgentTaskResult model — 任务执行结果行数据"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


class AgentTaskResult(CoreModel):
    """Agent 任务执行结果—分片存储""" ""
    exec_id = models.CharField(max_length=64, db_index=True, verbose_name="执行 ID")
    seq = models.IntegerField(default=1, verbose_name="分片序号")
    is_final = models.BooleanField(default=False, verbose_name="是否最终片")
    stdout = models.TextField(blank=True, default='', verbose_name="stdout")
    stderr = models.TextField(blank=True, default='', verbose_name="stderr")
    received_at = models.DateTimeField(null=True, blank=True,
                                       verbose_name="Server 收到时间")
    pushed_at = models.DateTimeField(null=True, blank=True,
                                     verbose_name="推送前端时间")

    class Meta:
        db_table = table_prefix + "agent_task_result"
        verbose_name = "Agent 任务结果"
        verbose_name_plural = verbose_name
        ordering = ['exec_id', 'seq']
        indexes = [
            models.Index(fields=['exec_id', 'seq']),
        ]
