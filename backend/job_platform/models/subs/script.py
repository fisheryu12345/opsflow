# -*- coding: utf-8 -*-
"""Script models — Script, ScriptVersion, ScriptReference

脚本管理：脚本主表、版本管理、引用追踪
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)

FSM = 'job_platform_script_models'


# ──────────────────────────────────────────────
#  Script — 脚本主表
# ──────────────────────────────────────────────

class Script(CoreModel):
    """脚本管理 — 可复用的执行脚本单元"""
    script_type_choices = (
        ('shell', 'Shell'),
        ('python', 'Python'),
        ('powershell', 'PowerShell'),
        ('bat', 'Batch'),
        ('sql', 'SQL'),
    )
    category_choices = (
        ('builtin', '内置'),
        ('public', '公开'),
        ('private', '私有'),
    )
    status_choices = (
        ('draft', '草稿'),
        ('online', '已发布'),
        ('disabled', '已禁用'),
    )

    name = models.CharField(max_length=255, verbose_name='脚本名称')
    description = models.TextField(null=True, blank=True, verbose_name='描述')
    script_type = models.CharField(max_length=32, choices=script_type_choices,
                                   default='shell', verbose_name='脚本类型')
    content = models.TextField(verbose_name='脚本内容')
    params_schema = models.JSONField(default=dict, verbose_name='参数 Schema',
                                     help_text='定义脚本参数的 JSON Schema，用于前端动态表单')
    tags = models.JSONField(default=list, verbose_name='标签')
    category = models.CharField(max_length=32, choices=category_choices,
                                default='private', verbose_name='分类')
    status = models.CharField(max_length=32, choices=status_choices,
                              default='draft', verbose_name='状态')
    current_version = models.CharField(max_length=32, default='1.0.0',
                                       verbose_name='当前版本')

    class Meta:
        db_table = table_prefix + 'job_script'
        verbose_name = '脚本'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f'{self.name} v{self.current_version}'


# ──────────────────────────────────────────────
#  ScriptVersion — 脚本版本
# ──────────────────────────────────────────────

class ScriptVersion(CoreModel):
    """脚本版本 — 语义化版本管理"""
    status_choices = (
        ('draft', '草稿'),
        ('online', '已发布'),
        ('disabled', '已禁用'),
    )

    script = models.ForeignKey(Script, on_delete=models.CASCADE,
                               related_name='versions', verbose_name='关联脚本')
    version = models.CharField(max_length=32, verbose_name='版本号',
                               help_text='语义化版本号，如 "1.0.0"')
    content = models.TextField(verbose_name='版本内容快照')
    changelog = models.TextField(null=True, blank=True, verbose_name='变更说明')
    status = models.CharField(max_length=32, choices=status_choices,
                              default='draft', verbose_name='状态')

    class Meta:
        db_table = table_prefix + 'job_script_version'
        verbose_name = '脚本版本'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']
        unique_together = [('script', 'version')]

    def __str__(self):
        return f'{self.script.name} v{self.version}'


# ──────────────────────────────────────────────
#  ScriptReference — 脚本引用追踪
# ──────────────────────────────────────────────

class ScriptReference(CoreModel):
    """脚本引用追踪 — 记录脚本被哪些模板/方案引用"""
    reference_type_choices = (
        ('template', '作业模板'),
        ('plan', '执行方案'),
        ('step', '步骤'),
    )

    script = models.ForeignKey(Script, on_delete=models.CASCADE,
                               related_name='references', verbose_name='关联脚本')
    reference_type = models.CharField(max_length=32, choices=reference_type_choices,
                                      verbose_name='引用类型')
    reference_id = models.IntegerField(verbose_name='引用对象 ID')
    reference_name = models.CharField(max_length=255, verbose_name='引用对象名称',
                                      help_text='冗余存储，方便展示')

    class Meta:
        db_table = table_prefix + 'job_script_reference'
        verbose_name = '脚本引用'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']
        indexes = [
            models.Index(fields=['script', 'reference_type']),
        ]

    def __str__(self):
        return f'{self.script.name} ← {self.reference_name}({self.reference_type})'
