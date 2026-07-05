# -*- coding: utf-8 -*-
"""ITSM Transition model — 节点间连线定义"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class Transition(CoreModel):
    """节点间流转线 — 可选条件表达式"""
    CONDITION_TYPE_CHOICES = (
        ('default', '默认'),
        ('by_field', '字段判断'),
    )

    workflow = models.ForeignKey('itsm.Workflow', on_delete=models.CASCADE,
                                 related_name='transitions', verbose_name="所属流程")
    name = models.CharField(max_length=64, blank=True, default='', verbose_name="连线名称")
    from_state = models.ForeignKey('itsm.State', on_delete=models.CASCADE,
                                   related_name='outgoing', verbose_name="源节点")
    to_state = models.ForeignKey('itsm.State', on_delete=models.CASCADE,
                                 related_name='incoming', verbose_name="目标节点")
    from_node_key = models.CharField(max_length=32, null=True, blank=True, db_index=True,
                                     verbose_name="源节点标识")
    to_node_key = models.CharField(max_length=32, null=True, blank=True, db_index=True,
                                   verbose_name="目标节点标识")
    condition = models.JSONField(default=dict, verbose_name="条件表达式")
    condition_type = models.CharField(
        max_length=16, default='default',
        choices=CONDITION_TYPE_CHOICES,
        verbose_name="条件类型",
    )
    direction = models.CharField(max_length=16, default='FORWARD', verbose_name="方向")

    class Meta:
        db_table = table_prefix + "itsm_workflow_transition"
        verbose_name = "流程连线"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.from_state.name} → {self.to_state.name}"
