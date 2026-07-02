# -*- coding: utf-8 -*-
"""ShieldPlan model — 告警静默/屏蔽计划"""

from django.db import models
from common.utils.models import table_prefix


class ShieldPlan(models.Model):
    """告警静默/屏蔽计划 — 在指定时间范围内屏蔽符合条件的告警"""

    SHIELD_TYPE_CHOICES = (
        ("strategy", "按策略"),
        ("target", "按目标"),
        ("tag", "按标签"),
        ("global", "全局"),
    )

    name = models.CharField(max_length=255, verbose_name="计划名称")
    bk_biz_id = models.IntegerField(verbose_name="业务ID", db_index=True)
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")
    shield_type = models.CharField(max_length=32, choices=SHIELD_TYPE_CHOICES,
                                   default="strategy", verbose_name="屏蔽类型")
    conditions = models.JSONField(default=dict, verbose_name="屏蔽条件",
                                  help_text="如 {'strategy_id': 1, 'target': '192.168.1.1'}")
    time_range = models.JSONField(null=True, blank=True, verbose_name="一次性时间范围",
                                  help_text="如 {'start': '2024-01-01T00:00:00Z', 'end': '2024-01-02T00:00:00Z'}")
    schedule = models.JSONField(null=True, blank=True, verbose_name="周期性cron配置",
                                help_text="如 {'cron': '0 22 * * *', 'duration': 480}")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    create_user = models.CharField(max_length=128, blank=True, default="", verbose_name="创建人")

    class Meta:
        db_table = table_prefix + "monitor_shield_plan"
        verbose_name = "告警屏蔽计划"
        verbose_name_plural = verbose_name
        ordering = ["-id"]

    def __str__(self):
        return self.name
