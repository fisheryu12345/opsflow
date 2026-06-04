# -*- coding: utf-8 -*-
"""Base/shared models — Account, FileSource, DangerousCmdRule, DangerousCheckLog

基础/共享模型：账号管理、文件源配置、高危命令规则、检测日志
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)

FSM = 'job_platform_base_models'


# ──────────────────────────────────────────────
#  Account — 凭据管理
# ──────────────────────────────────────────────

class Account(CoreModel):
    """执行账号 — SSH/数据库凭据，AES 加密存储"""
    protocol_choices = (
        ('ssh', 'SSH'),
        ('winrm', 'WinRM'),
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
    )
    credential_type_choices = (
        ('password', '密码'),
        ('key', '私钥'),
        ('secret', '密钥'),
    )
    category_choices = (
        ('system', '系统账户'),
        ('database', '数据库账户'),
        ('cloud', '云平台'),
    )
    scope_choices = (
        ('global', '全局'),
        ('project', '项目'),
    )

    name = models.CharField(max_length=255, verbose_name='账号别名',
                            help_text='如 "prod-root"')
    protocol = models.CharField(max_length=32, choices=protocol_choices,
                                default='ssh', verbose_name='协议')
    username = models.CharField(max_length=255, verbose_name='用户名')
    password = models.TextField(verbose_name='密码(加密存储)',
                                help_text='AES-256 加密后存储')
    ssh_key = models.TextField(null=True, blank=True, verbose_name='SSH 私钥(加密)')
    port = models.IntegerField(default=22, verbose_name='端口')
    credential_type = models.CharField(max_length=32, choices=credential_type_choices,
                                       default='password', verbose_name='凭证类型')
    category = models.CharField(max_length=32, choices=category_choices,
                                default='system', verbose_name='分类')
    scope = models.CharField(max_length=32, choices=scope_choices,
                             default='global', verbose_name='作用域')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        db_table = table_prefix + 'job_account'
        verbose_name = '执行账号'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f'{self.name} ({self.username}@{self.protocol})'


# ──────────────────────────────────────────────
#  FileSource — 预配置文件源
# ──────────────────────────────────────────────

class FileSource(CoreModel):
    """文件源 — S3/FTP/Samba/NFS 等预配置数据源"""
    source_type_choices = (
        ('s3', 'Amazon S3'),
        ('ftp', 'FTP'),
        ('samba', 'Samba'),
        ('nfs', 'NFS'),
        ('custom', '自定义'),
    )
    credential_type_choices = (
        ('password', '密码'),
        ('key', '密钥'),
        ('secret', 'Secret'),
    )

    name = models.CharField(max_length=255, verbose_name='文件源名称')
    description = models.TextField(null=True, blank=True, verbose_name='描述')
    source_type = models.CharField(max_length=32, choices=source_type_choices,
                                   default='s3', verbose_name='文件源类型')
    config = models.JSONField(default=dict, verbose_name='连接配置',
                              help_text='按类型存储连接参数')
    credential_type = models.CharField(max_length=32, choices=credential_type_choices,
                                       default='password', verbose_name='凭证类型')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        db_table = table_prefix + 'job_file_source'
        verbose_name = '文件源'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f'{self.name} ({self.source_type})'


# ──────────────────────────────────────────────
#  DangerousCmdRule — 高危命令规则
# ──────────────────────────────────────────────

class DangerousCmdRule(CoreModel):
    """高危命令检测规则 — 关键字/正则匹配，拦截/审批/警告"""
    action_choices = (
        ('reject', '直接拦截'),
        ('approval', '需要审批'),
        ('warn', '仅警告'),
    )
    script_type_choices = (
        ('shell', 'Shell'),
        ('python', 'Python'),
        ('sql', 'SQL'),
        ('all', '全部'),
    )
    severity_choices = (
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '严重'),
    )

    name = models.CharField(max_length=255, verbose_name='规则名称')
    description = models.TextField(null=True, blank=True, verbose_name='规则说明')
    pattern = models.CharField(max_length=512, verbose_name='匹配模式',
                               help_text='关键词或正则表达式')
    is_regex = models.BooleanField(default=False, verbose_name='是否正则匹配')
    script_type = models.CharField(max_length=32, choices=script_type_choices,
                                   default='all', verbose_name='适用脚本类型')
    action = models.CharField(max_length=32, choices=action_choices,
                              default='reject', verbose_name='处理方式')
    severity = models.CharField(max_length=32, choices=severity_choices,
                                default='high', verbose_name='严重级别')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        db_table = table_prefix + 'job_dangerous_cmd_rule'
        verbose_name = '高危命令规则'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f'{self.name} [{self.action}]'


# ──────────────────────────────────────────────
#  DangerousCheckLog — 高危检测记录
# ──────────────────────────────────────────────

class DangerousCheckLog(CoreModel):
    """高危命令检测记录 — 每次检测的详细日志"""
    action_choices = (
        ('allow', '放行'),
        ('reject', '拦截'),
        ('approval', '需审批'),
        ('warn', '警告'),
    )

    script_content = models.TextField(verbose_name='被检测脚本',
                                      help_text='实际被检测的脚本内容片段')
    script_type = models.CharField(max_length=32, default='shell', verbose_name='脚本类型')
    rule_hits = models.JSONField(default=list, verbose_name='命中规则',
                                 help_text='命中的规则列表 [{rule_id, name, action}]')
    ai_result = models.JSONField(default=dict, verbose_name='AI 检测结果',
                                 help_text='{risk_level, reason, suggestion}')
    final_action = models.CharField(max_length=32, choices=action_choices,
                                    default='allow', verbose_name='最终处理')
    execution = models.ForeignKey('job_platform.JobExecution',
                                  null=True, on_delete=models.SET_NULL,
                                  related_name='dangerous_checks',
                                  verbose_name='关联执行')

    class Meta:
        db_table = table_prefix + 'job_dangerous_check_log'
        verbose_name = '高危检测记录'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f'Check[{self.final_action}] at {self.create_datetime}'
