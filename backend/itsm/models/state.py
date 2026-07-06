# -*- coding: utf-8 -*-
"""ITSM State model — 流程节点定义"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class State(CoreModel):
    """流程节点 — 对应 pipeline 中的一个活动"""
    TYPE_CHOICES = (
        ('START', '开始'),
        ('END', '结束'),
        ('NORMAL', '普通节点'),
        ('APPROVAL', '审批'),
        ('SIGN', '会签'),
        ('TASK', '自动任务'),
        ('CONDITIONAL_PARALLEL', '条件并行网关'),
        ('EXCLUSIVE', '排他网关'),
        ('PARALLEL', '并行网关'),
        ('COVERAGE', '汇聚网关'),
    )
    PROCESSOR_TYPE_CHOICES = (
        ('PERSON', '指定人员'),
        ('STARTER', '提单人'),
        ('STARTER_LEADER', '提单人上级'),
        ('ROLE', '角色'),
        ('ORGANIZATION', '组织架构'),
        ('VARIABLE', '变量引用'),
    )
    DISTRIBUTE_CHOICES = (
        ('PROCESS', '直接处理'),
        ('CLAIM_THEN_PROCESS', '认领后处理'),
        ('DISTRIBUTE_THEN_PROCESS', '分派后处理'),
    )
    workflow = models.ForeignKey('itsm.Workflow', on_delete=models.CASCADE,
                                 related_name='states', verbose_name="所属流程")
    node_key = models.CharField(max_length=32, null=True, blank=True, db_index=True,
                                verbose_name="前端节点标识")
    name = models.CharField(max_length=128, verbose_name="节点名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="节点名称(英文)")
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, verbose_name="节点类型")
    is_builtin = models.BooleanField(default=False, verbose_name="内置节点")

    # 处理人配置
    processors_type = models.CharField(max_length=32, choices=PROCESSOR_TYPE_CHOICES,
                                        default='PERSON', verbose_name="处理人类型")
    processors = models.TextField(blank=True, default='', verbose_name="处理人配置")
    distribute_type = models.CharField(max_length=32, choices=DISTRIBUTE_CHOICES,
                                        default='PROCESS', verbose_name="分配方式")

    # 会签/审批配置
    is_multi = models.BooleanField(default=False, verbose_name="是否多签")
    is_sequential = models.BooleanField(default=False, verbose_name="串行会签")
    finish_condition = models.JSONField(default=dict, verbose_name="完成条件")
    is_allow_skip = models.BooleanField(default=False, verbose_name="允许跳过")

    # 字段配置与扩展
    fields = models.JSONField(default=list, verbose_name="表单字段定义")
    extras = models.JSONField(default=dict, verbose_name="扩展配置")
    api_instance_id = models.IntegerField(null=True, blank=True, verbose_name="API 实例")

    class Meta:
        db_table = table_prefix + "itsm_workflow_state"
        verbose_name = "流程节点"
        verbose_name_plural = verbose_name
        ordering = ['id']
        unique_together = [('workflow', 'node_key')]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.name}"
