# -*- coding: utf-8 -*-
"""Template/Plan models — Template, Plan, Variable

作业编排核心：作业模板、执行方案、全局变量
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)

FSM = 'job_platform_template_models'


# ──────────────────────────────────────────────
#  Template — 作业模板
# ──────────────────────────────────────────────

class Template(CoreModel):
    """作业模板 — 可编排多步骤的作业定义模板"""
    status_choices = (
        ('draft', '草稿'),
        ('published', '已发布'),
        ('deprecated', '已弃用'),
    )

    name = models.CharField(max_length=255, verbose_name='模板名称')
    description = models.TextField(null=True, blank=True, verbose_name='描述')
    status = models.CharField(max_length=32, choices=status_choices,
                              default='draft', verbose_name='状态')
    category = models.CharField(max_length=50, null=True, blank=True, verbose_name='分类')
    tags = models.JSONField(default=list, verbose_name='标签')
    version = models.CharField(max_length=20, default='1.0', verbose_name='版本号')
    # 链表头尾指针 — 使用字符串引用避免循环依赖
    first_step = models.ForeignKey('job_platform.Step', null=True,
                                   on_delete=models.SET_NULL,
                                   related_name='+', verbose_name='首个步骤')
    last_step = models.ForeignKey('job_platform.Step', null=True,
                                  on_delete=models.SET_NULL,
                                  related_name='+', verbose_name='最后步骤')

    class Meta:
        db_table = table_prefix + 'job_template'
        verbose_name = '作业模板'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f'{self.name} ({self.status})'


# ──────────────────────────────────────────────
#  Plan — 执行方案（继承自模板）
# ──────────────────────────────────────────────

class Plan(CoreModel):
    """执行方案 — 从模板派生的可执行配置"""
    plan_type_choices = (
        ('normal', '普通'),
        ('debug', '调试'),
    )

    template = models.ForeignKey(Template, on_delete=models.CASCADE,
                                 related_name='plans', verbose_name='来源模板')
    name = models.CharField(max_length=255, verbose_name='方案名称')
    description = models.TextField(null=True, blank=True, verbose_name='描述')
    plan_type = models.CharField(max_length=32, choices=plan_type_choices,
                                 default='normal', verbose_name='方案类型')
    enable_step_ids = models.JSONField(default=list, verbose_name='启用步骤 ID 列表',
                                       help_text='方案中实际执行的步骤 ID')
    is_debug = models.BooleanField(default=False, verbose_name='是否为调试模式')

    class Meta:
        db_table = table_prefix + 'job_plan'
        verbose_name = '执行方案'
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f'{self.name} (Plan of {self.template.name})'


# ──────────────────────────────────────────────
#  Variable — 全局变量
# ──────────────────────────────────────────────

class Variable(CoreModel):
    """全局变量 — 模板/方案级别的参数变量"""
    var_type_choices = (
        ('string', '字符串'),
        ('namespace', '命名空间'),
        ('cipher', '密文'),
        ('host_list', '主机列表'),
    )

    template = models.ForeignKey(Template, null=True, blank=True,
                                 on_delete=models.CASCADE,
                                 related_name='variables', verbose_name='所属模板')
    plan = models.ForeignKey(Plan, null=True, blank=True,
                             on_delete=models.CASCADE,
                             related_name='variables', verbose_name='所属方案')
    name = models.CharField(max_length=255, verbose_name='变量名')
    var_type = models.CharField(max_length=32, choices=var_type_choices,
                                default='string', verbose_name='变量类型')
    default_value = models.JSONField(null=True, blank=True, verbose_name='默认值')
    changeable = models.BooleanField(default=True, verbose_name='执行时允许修改')
    required = models.BooleanField(default=False, verbose_name='是否必填')
    follow_template = models.BooleanField(default=True, verbose_name='跟随模板值',
                                          help_text='方案是否跟随模板的变量值')
    description = models.TextField(null=True, blank=True, verbose_name='变量说明')

    class Meta:
        db_table = table_prefix + 'job_variable'
        verbose_name = '全局变量'
        verbose_name_plural = verbose_name
        ordering = ['template_id', 'plan_id', 'id']

    def __str__(self):
        return f'{self.name} ({self.var_type})'
