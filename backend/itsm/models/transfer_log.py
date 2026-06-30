# -*- coding: utf-8 -*-
"""TicketTransferLog model — 工单转派/升级审计日志"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


class TicketTransferLog(CoreModel):
    """工单转派记录 — 手动转派 + 自动升级 + 自动分派"""
    TRANSFER_TYPE_CHOICES = (
        ('manual', '手动转派'),
        ('auto_escalation', '自动升级'),
        ('auto_assign', '自动分派'),
    )
    ticket = models.ForeignKey(
        'itsm.Ticket', on_delete=models.CASCADE, related_name='transfer_logs',
        verbose_name="关联工单",
    )
    from_user = models.ForeignKey(
        'system.Users', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name="转出人",
    )
    to_user = models.ForeignKey(
        'system.Users', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name="转入人",
    )
    from_group = models.ForeignKey(
        'itsm.SkillGroup', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name="转出技能组",
    )
    to_group = models.ForeignKey(
        'itsm.SkillGroup', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name="转入技能组",
    )
    reason = models.TextField(blank=True, default='', verbose_name="原因")
    transfer_type = models.CharField(
        max_length=32, choices=TRANSFER_TYPE_CHOICES, default='manual',
        verbose_name="转派类型",
    )

    class Meta:
        db_table = table_prefix + "itsm_ticket_transfer_log"
        verbose_name = "工单转派记录"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"#{self.ticket_id} → {self.to_user_id} ({self.get_transfer_type_display()})"
