# -*- coding: utf-8 -*-
"""ApprovalDelegate model — 审批委托

允许用户将审批权限临时委托给其他用户，支持按工单类型和日期范围限制。
"""

from django.conf import settings
from django.db import models

from common.utils.models import CoreModel, table_prefix


class ApprovalDelegate(CoreModel):
    """审批委托 — 将审批权限临时委托给其他用户"""
    TICKET_TYPE_CHOICES = (
        ('', '全部类型'),
        ('change', '变更申请'),
        ('incident', '事件工单'),
        ('request', '服务请求'),
        ('problem', '问题管理'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegation_from',
        verbose_name="委托人",
    )
    delegate_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegation_to',
        verbose_name="被委托人",
    )
    date_from = models.DateTimeField(verbose_name="委托开始时间")
    date_to = models.DateTimeField(verbose_name="委托结束时间")
    ticket_type = models.CharField(
        max_length=32, choices=TICKET_TYPE_CHOICES,
        default='', blank=True,
        verbose_name="委托工单类型（空=全部）",
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    remark = models.TextField(blank=True, default='', verbose_name="备注")

    class Meta:
        db_table = table_prefix + "itsm_approval_delegate"
        verbose_name = "审批委托"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.user} → {self.delegate_to} ({self.date_from}~{self.date_to})"
