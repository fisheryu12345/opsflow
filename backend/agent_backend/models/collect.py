# -*- coding: utf-8 -*-
"""AgentCollect model — CMDB 采集记录"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class AgentCollect(CoreModel):
    """Agent CMDB 采集配置与记录"""

    collect_type_choices = (
        ('host_info', '主机信息'),
        ('process', '进程快照'),
        ('disk', '磁盘'),
        ('network', '网络'),
        ('package', '软件包'),
    )

    agent = models.ForeignKey(
        'AgentInstance', on_delete=models.CASCADE,
        related_name='collects', verbose_name="所属 Agent"
    )
    collect_type = models.CharField(max_length=32, choices=collect_type_choices,
                                    verbose_name="采集类型")
    collect_interval = models.IntegerField(default=300, verbose_name="采集间隔(秒)")
    last_collect = models.DateTimeField(null=True, blank=True,
                                        verbose_name="最后采集")
    last_data = models.JSONField(default=dict, verbose_name="最新数据快照")
    status = models.CharField(max_length=16, default='enabled',
                              choices=(('enabled', '启用'), ('disabled', '禁用')),
                              verbose_name="状态")

    class Meta:
        db_table = table_prefix + "agent_collect"
        verbose_name = "Agent 采集记录"
        verbose_name_plural = verbose_name
        unique_together = [('agent', 'collect_type')]
