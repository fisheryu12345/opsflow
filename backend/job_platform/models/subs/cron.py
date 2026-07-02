# -*- coding: utf-8 -*-
"""Cron models — CronJob, CronJobExecution

定时作业：Cron 调度配置、执行历史
"""

import logging

from django.db import models
from common.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)

FSM = 'job_platform_cron_models'


# ──────────────────────────────────────────────
#  CronJob — 定时作业配置
# ──────────────────────────────────────────────

class CronJob(CoreModel):
    """定时作业 — Cron 调度任务"""

    name = models.CharField(max_length=255, verbose_name='任务名称')
    description = models.TextField(null=True, blank=True, verbose_name='描述')
    plan = models.ForeignKey('job_platform.Plan', null=True, blank=True,
                             on_delete=models.SET_NULL,
                             related_name='cron_jobs', verbose_name='关联执行方案')
    script = models.ForeignKey('job_platform.Script', null=True, blank=True,
                               on_delete=models.SET_NULL,
                               related_name='+', verbose_name='直接执行脚本',
                               help_text='不经过模板方案的快速定时执行')
    cron_expression = models.CharField(max_length=64, verbose_name='Cron 表达式',
                                       help_text='标准 5 位 cron 表达式')
    timezone = models.CharField(max_length=64, default='Asia/Shanghai',
                                verbose_name='时区')
    variables_override = models.JSONField(default=dict, verbose_name='变量覆盖')
    target_override = models.JSONField(default=dict, verbose_name='目标覆盖')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='生效开始')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='生效结束')
    misfire_grace = models.IntegerField(default=300, verbose_name='容错时间(秒)',
                                        help_text='超出此时间则跳过')
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name='上次执行')
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name='下次执行')

    class Meta:
        db_table = table_prefix + 'job_cron_job'
        verbose_name = '定时作业'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f'{self.name} ({self.cron_expression})'


# ──────────────────────────────────────────────
#  CronJobExecution — 定时执行历史
# ──────────────────────────────────────────────

class CronJobExecution(CoreModel):
    """定时作业执行历史"""
    status_choices = (
        ('pending', '等待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('skipped', '已跳过'),
        ('missed', '已错过'),
    )

    cron_job = models.ForeignKey(CronJob, on_delete=models.CASCADE,
                                 related_name='execution_history',
                                 verbose_name='关联定时作业')
    execution = models.ForeignKey('job_platform.JobExecution',
                                  null=True, blank=True,
                                  on_delete=models.SET_NULL,
                                  related_name='+', verbose_name='关联执行记录')
    status = models.CharField(max_length=32, choices=status_choices,
                              default='pending', verbose_name='状态')
    scheduled_time = models.DateTimeField(verbose_name='计划执行时间')
    actual_time = models.DateTimeField(null=True, blank=True, verbose_name='实际执行时间')
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息')

    class Meta:
        db_table = table_prefix + 'job_cron_job_execution'
        verbose_name = '定时执行历史'
        verbose_name_plural = verbose_name
        ordering = ['-scheduled_time']

    def __str__(self):
        return f'{self.cron_job.name} @ {self.scheduled_time} [{self.status}]'
