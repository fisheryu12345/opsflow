# -*- coding: utf-8 -*-
"""Job platform — batch execution, script management, file distribution

作业平台：批量脚本执行、文件分发、高危命令拦截、执行账户管理
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)


class Script(CoreModel):
    """脚本管理"""
    script_type_choices = (
        ('shell', 'Shell'),
        ('python', 'Python'),
        ('powershell', 'PowerShell'),
        ('bat', 'Batch'),
        ('sql', 'SQL'),
    )

    name = models.CharField(max_length=255, verbose_name="脚本名称")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    script_type = models.CharField(max_length=32, choices=script_type_choices, default='shell', verbose_name="脚本类型")
    content = models.TextField(verbose_name="脚本内容")
    params_schema = models.JSONField(default=dict, verbose_name="参数 Schema",
                                     help_text="定义脚本参数的 JSON Schema")
    version = models.CharField(max_length=32, default='1.0', verbose_name="版本")
    tags = models.JSONField(default=list, verbose_name="标签")
    is_public = models.BooleanField(default=True, verbose_name="是否公开")
    is_builtin = models.BooleanField(default=False, verbose_name="是否内置")

    class Meta:
        db_table = table_prefix + "job_script"
        verbose_name = "脚本"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.name} v{self.version}"


class JobDefinition(CoreModel):
    """作业定义 — 可在多台主机上执行的任务模板"""
    executor_choices = (
        ('ssh', 'SSH 远程执行'),
        ('local', '本地执行'),
        ('ansible', 'Ansible Playbook'),
    )

    name = models.CharField(max_length=255, verbose_name="作业名称")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    executor = models.CharField(max_length=32, choices=executor_choices, default='ssh', verbose_name="执行方式")
    script = models.ForeignKey(Script, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='jobs', verbose_name="关联脚本")
    command = models.TextField(null=True, blank=True, verbose_name="内联命令",
                                help_text="直接填写命令，与脚本二选一")
    params = models.JSONField(default=dict, verbose_name="默认参数")
    timeout_seconds = models.IntegerField(default=300, verbose_name="超时时间(秒)")
    need_approval = models.BooleanField(default=False, verbose_name="需要审批")
    run_as = models.CharField(max_length=128, default='root', verbose_name="执行用户")
    tags = models.JSONField(default=list, verbose_name="标签")

    class Meta:
        db_table = table_prefix + "job_definition"
        verbose_name = "作业定义"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return self.name


class JobExecution(CoreModel):
    """作业执行记录"""
    status_choices = (
        ('pending', '等待执行'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('timeout', '超时'),
        ('cancelled', '已取消'),
        ('approving', '待审批'),
    )

    job = models.ForeignKey(JobDefinition, on_delete=models.SET_NULL, null=True,
                             related_name='executions', verbose_name="关联作业")
    status = models.CharField(max_length=32, choices=status_choices, default='pending', verbose_name="状态")
    target_hosts = models.JSONField(default=list, verbose_name="目标主机",
                                     help_text="主机 IP 或 CMDB host_id 列表")
    params = models.JSONField(default=dict, verbose_name="执行参数")
    result_summary = models.TextField(null=True, blank=True, verbose_name="结果摘要")
    result_detail = models.JSONField(default=dict, verbose_name="详细结果(按主机)")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    exit_code = models.IntegerField(null=True, blank=True, verbose_name="退出码")
    executor = models.CharField(max_length=32, default='ssh', verbose_name="执行方式")
    run_as = models.CharField(max_length=128, default='root', verbose_name="执行用户")
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")

    class Meta:
        db_table = table_prefix + "job_execution"
        verbose_name = "作业执行记录"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.job.name if self.job else 'N/A'} [{self.status}]"


class DangerousCmdRule(CoreModel):
    """高危命令规则 — 关键词/正则匹配，拦截或审批"""
    action_choices = (
        ('reject', '直接拦截'),
        ('approval', '需要审批'),
        ('warn', '仅警告'),
    )

    name = models.CharField(max_length=255, verbose_name="规则名称")
    pattern = models.CharField(max_length=512, verbose_name="匹配模式",
                                help_text="关键词或正则表达式")
    is_regex = models.BooleanField(default=False, verbose_name="是否正则")
    action = models.CharField(max_length=32, choices=action_choices, default='reject', verbose_name="处理方式")
    severity = models.CharField(max_length=32, default='high', verbose_name="严重级别")
    description = models.TextField(null=True, blank=True, verbose_name="规则说明")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "job_dangerous_cmd_rule"
        verbose_name = "高危命令规则"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return self.name
