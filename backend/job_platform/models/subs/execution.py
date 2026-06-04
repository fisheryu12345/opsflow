# -*- coding: utf-8 -*-
"""Execution models — JobExecution, StepExecution

执行实例：作业执行记录、步骤执行记录
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)

FSM = 'job_platform_exec_models'


# ──────────────────────────────────────────────
#  JobExecution — 作业执行实例
# ──────────────────────────────────────────────

class JobExecution(CoreModel):
    """作业执行实例 — 记录一次完整的作业执行过程"""
    status_choices = (
        ('pending', '等待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('stopped', '已停止'),
        ('timeout', '超时'),
        ('approving', '待审批'),
        ('confirmed_terminated', '审批终止'),
        ('ignore_error', '已忽略错误'),
    )
    executor_choices = (
        ('ssh', 'SSH'),
        ('ansible', 'Ansible'),
        ('agent', 'Agent'),
    )
    triggered_by_choices = (
        ('manual', '手动'),
        ('cron', '定时'),
        ('api', 'API'),
    )

    plan = models.ForeignKey('job_platform.Plan', null=True, blank=True,
                             on_delete=models.SET_NULL,
                             related_name='executions', verbose_name='关联方案')
    template = models.ForeignKey('job_platform.Template', null=True, blank=True,
                                 on_delete=models.SET_NULL,
                                 related_name='executions', verbose_name='关联模板')
    status = models.CharField(max_length=32, choices=status_choices,
                              default='pending', verbose_name='执行状态')
    current_step_index = models.IntegerField(default=0, verbose_name='当前步骤索引')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    executor = models.CharField(max_length=32, choices=executor_choices,
                                default='ssh', verbose_name='执行通道')
    variables = models.JSONField(default=dict, verbose_name='运行时变量快照')
    triggered_by = models.CharField(max_length=32, choices=triggered_by_choices,
                                    default='manual', verbose_name='触发方式')
    result_summary = models.TextField(null=True, blank=True, verbose_name='结果摘要')
    # 执行目标快照
    target_config = models.JSONField(default=dict, verbose_name='目标配置',
                                     help_text='执行时的目标主机配置快照')
    resolved_targets = models.JSONField(default=list, verbose_name='解析后目标列表',
                                        help_text='CMDB 解析后的具体主机列表')

    class Meta:
        db_table = table_prefix + 'job_execution'
        verbose_name = '作业执行记录'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        source = self.plan or self.template
        return f'Exec[{self.status}]: {source}'

    @property
    def total_time(self):
        """执行耗时(秒)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


# ──────────────────────────────────────────────
#  StepExecution — 步骤执行记录
# ──────────────────────────────────────────────

class StepExecution(CoreModel):
    """步骤执行记录 — 单个步骤的执行详情"""
    status_choices = (
        ('pending', '等待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('skipped', '已跳过'),
        ('waiting_user', '等待审批'),
        ('timeout', '超时'),
        ('ignored_error', '已忽略错误'),
    )

    execution = models.ForeignKey(JobExecution, on_delete=models.CASCADE,
                                  related_name='step_executions',
                                  verbose_name='关联执行')
    step = models.ForeignKey('job_platform.Step', null=True, blank=True,
                             on_delete=models.SET_NULL,
                             related_name='step_executions', verbose_name='关联步骤')
    step_type = models.CharField(max_length=32, verbose_name='步骤类型',
                                 help_text='冗余存储，步骤删除后仍可识别')
    step_name = models.CharField(max_length=255, default='', verbose_name='步骤名称')
    status = models.CharField(max_length=32, choices=status_choices,
                              default='pending', verbose_name='状态')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    exit_code = models.IntegerField(null=True, blank=True, verbose_name='退出码')
    # 结果存储
    host_results = models.JSONField(default=dict, verbose_name='按主机结果',
                                    help_text='{host_ip: {exit_code, stdout, stderr}}')
    result_summary = models.TextField(null=True, blank=True, verbose_name='结果摘要')
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息')
    # Celery task ID，用于取消
    task_id = models.CharField(max_length=255, null=True, blank=True,
                               verbose_name='Task ID')
    # 审批相关
    itsm_ticket_id = models.CharField(max_length=255, null=True, blank=True,
                                      verbose_name='ITSM 工单 ID')
    approved_by = models.CharField(max_length=255, null=True, blank=True,
                                   verbose_name='审批人')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审批时间')

    class Meta:
        db_table = table_prefix + 'job_step_execution'
        verbose_name = '步骤执行记录'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return f'StepExec[{self.status}]: {self.step_name}'

    @property
    def total_hosts(self):
        return len(self.host_results) if self.host_results else 0

    @property
    def success_hosts(self):
        if not self.host_results:
            return 0
        return sum(1 for r in self.host_results.values()
                   if r.get('exit_code', -1) == 0)
