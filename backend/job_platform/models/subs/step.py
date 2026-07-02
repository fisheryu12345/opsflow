# -*- coding: utf-8 -*-
"""Step models — Step, ScriptStep, FileStep, ApprovalStep

步骤模型：步骤链表节点 + 三种步骤类型的详细信息
"""

import logging

from django.db import models
from common.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)

FSM = 'job_platform_step_models'


# ──────────────────────────────────────────────
#  Step — 步骤链表节点
# ──────────────────────────────────────────────

class Step(CoreModel):
    """步骤 — 双向链表节点，支持 script/file/approval 三种类型"""
    step_type_choices = (
        ('script', '脚本执行'),
        ('file', '文件分发'),
        ('approval', '人工审批'),
    )

    template = models.ForeignKey('job_platform.Template', null=True, blank=True,
                                 on_delete=models.CASCADE,
                                 related_name='steps', verbose_name='所属模板')
    plan = models.ForeignKey('job_platform.Plan', null=True, blank=True,
                             on_delete=models.CASCADE,
                             related_name='steps', verbose_name='所属方案')
    type = models.CharField(max_length=32, choices=step_type_choices,
                            verbose_name='步骤类型')
    name = models.CharField(max_length=255, default='', verbose_name='步骤名称')
    # 链表指针
    previous_step = models.ForeignKey('self', null=True, blank=True,
                                      on_delete=models.SET_NULL,
                                      related_name='+', verbose_name='前驱步骤')
    next_step = models.ForeignKey('self', null=True, blank=True,
                                  on_delete=models.SET_NULL,
                                  related_name='+', verbose_name='后继步骤')
    template_step_id = models.IntegerField(null=True, blank=True,
                                           verbose_name='模板步骤 ID',
                                           help_text='方案步骤记录的原始模板步骤 ID')
    enable = models.BooleanField(default=True, verbose_name='是否启用')
    ref_variables = models.JSONField(default=list, verbose_name='引用变量',
                                     help_text='此步骤引用的变量名列表 ["var1", "var2"]')

    class Meta:
        db_table = table_prefix + 'job_step'
        verbose_name = '步骤'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return f'{self.get_type_display()}: {self.name or self.id}'


# ──────────────────────────────────────────────
#  ScriptStep — 脚本步骤详情
# ──────────────────────────────────────────────

class ScriptStep(CoreModel):
    """脚本步骤 — 脚本执行相关的详细配置"""
    script_source_choices = (
        ('local', '本地脚本'),
        ('citing', '引用脚本库'),
        ('public', '公共脚本'),
    )
    language_choices = (
        ('shell', 'Shell'),
        ('python', 'Python'),
        ('powershell', 'PowerShell'),
        ('bat', 'Batch'),
        ('sql', 'SQL'),
    )

    step = models.OneToOneField(Step, on_delete=models.CASCADE,
                                related_name='script_step', verbose_name='关联步骤')
    script_source = models.CharField(max_length=32, choices=script_source_choices,
                                     default='citing', verbose_name='脚本来源')
    script = models.ForeignKey('job_platform.Script', null=True, blank=True,
                               on_delete=models.SET_NULL,
                               related_name='+', verbose_name='引用脚本')
    script_version_id = models.IntegerField(null=True, blank=True,
                                            verbose_name='引用脚本版本 ID')
    content = models.TextField(null=True, blank=True, verbose_name='脚本内容',
                               help_text='内联脚本内容；引用脚本时可为空')
    language = models.CharField(max_length=32, choices=language_choices,
                                default='shell', verbose_name='脚本语言')
    script_params = models.TextField(null=True, blank=True, verbose_name='脚本参数')
    timeout = models.IntegerField(default=300, verbose_name='超时时间(秒)')
    account = models.ForeignKey('job_platform.Account', null=True, blank=True,
                                on_delete=models.SET_NULL,
                                related_name='+', verbose_name='执行账号')
    ignore_error = models.BooleanField(default=False, verbose_name='失败时忽略')
    secure_param = models.BooleanField(default=False, verbose_name='参数是否敏感隐藏')

    class Meta:
        db_table = table_prefix + 'job_script_step'
        verbose_name = '脚本步骤'
        verbose_name_plural = verbose_name

    def __str__(self):
        source = self.get_script_source_display()
        return f'ScriptStep[{source}]: {self.step.name}'


# ──────────────────────────────────────────────
#  FileStep — 文件步骤详情
# ──────────────────────────────────────────────

class FileStep(CoreModel):
    """文件步骤 — 文件分发相关的详细配置"""
    transfer_mode_choices = (
        ('strict', '严谨模式'),
        ('force', '强制覆盖'),
        ('safe', '安全模式'),
    )

    step = models.OneToOneField(Step, on_delete=models.CASCADE,
                                related_name='file_step', verbose_name='关联步骤')
    file_sources = models.JSONField(default=list, verbose_name='文件源配置',
                                    help_text='[{type, files, account_id, file_source_id}]')
    destination_path = models.CharField(max_length=1024, verbose_name='目标路径')
    transfer_mode = models.CharField(max_length=32, choices=transfer_mode_choices,
                                     default='strict', verbose_name='传输模式')
    speed_limit = models.IntegerField(default=0, verbose_name='限速(KB/s)',
                                      help_text='0 表示不限速')
    account = models.ForeignKey('job_platform.Account', null=True, blank=True,
                                on_delete=models.SET_NULL,
                                related_name='+', verbose_name='目标端账号')

    class Meta:
        db_table = table_prefix + 'job_file_step'
        verbose_name = '文件步骤'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'FileStep: {self.step.name}'


# ──────────────────────────────────────────────
#  ApprovalStep — 审批步骤详情
# ──────────────────────────────────────────────

class ApprovalStep(CoreModel):
    """审批步骤 — 人工审批相关配置"""
    approval_type_choices = (
        ('anyone', '一人通过即可'),
        ('all', '需全部通过'),
    )
    notify_channel_choices = (
        ('email', '邮件'),
        ('dingtalk', '钉钉'),
        ('wechat', '企业微信'),
    )

    step = models.OneToOneField(Step, on_delete=models.CASCADE,
                                related_name='approval_step', verbose_name='关联步骤')
    approval_type = models.CharField(max_length=32, choices=approval_type_choices,
                                     default='anyone', verbose_name='审批方式')
    approvers = models.JSONField(default=list, verbose_name='审批人列表',
                                 help_text='用户 ID 或角色名列表')
    approval_message = models.TextField(verbose_name='审批说明',
                                        help_text='支持变量渲染')
    notify_channels = models.JSONField(default=list, verbose_name='通知渠道')

    class Meta:
        db_table = table_prefix + 'job_approval_step'
        verbose_name = '审批步骤'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'ApprovalStep: {self.step.name} ({self.get_approval_type_display()})'
