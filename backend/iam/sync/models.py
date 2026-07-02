from django.conf import settings
# -*- coding: utf-8 -*-
"""Mapping models for identity sync engine

Tracks the relationship between remote identity source entries
(LDAP DN, AD objectGUID, etc.) and local Dept/Users records.

These models enable incremental sync by keeping a snapshot of
remote attributes so the differ can detect changes efficiently.
"""

from django.db import models
from common.utils.models import table_prefix


def _sync_table(name: str) -> str:
    """Generate table name with prefix for sync models"""
    return table_prefix + f"iam_sync_{name}"


class DeptMapping(models.Model):
    """部门映射：追踪 LDAP DN → 本地 Dept 的关联

    每次同步时更新 remote_attrs 快照，
    diff 算法通过对比快照来判断是否需要更新。
    """
    source_instance = models.ForeignKey(
        'integration.ConnectorInstance',
        on_delete=models.CASCADE,
        related_name='dept_mappings',
        verbose_name="Source Instance",
        help_text="集成中心的连接器实例 / ConnectorInstance in Integration Hub",
        db_constraint=False,
    )
    dept = models.ForeignKey(
        'iam.IAMDept',
        on_delete=models.CASCADE,
        related_name='sync_mappings',
        verbose_name="Local Dept",
        help_text="本地的系统部门 / Local department record",
        db_constraint=False,
    )
    remote_dn = models.CharField(
        max_length=512,
        db_index=True,
        verbose_name="Remote DN",
        help_text="LDAP 中该部门的 Distinguished Name / LDAP DN",
    )
    remote_attrs = models.JSONField(
        default=dict,
        verbose_name="Remote Attributes",
        help_text="远端属性快照，用于 diff 对比 / Cached remote attributes for diff",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Created At",
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Updated At",
    )

    class Meta:
        db_table = _sync_table("dept_mapping")
        verbose_name = "Dept Mapping"
        verbose_name_plural = "Dept Mappings"
        unique_together = [('source_instance', 'remote_dn')]
        indexes = [
            models.Index(fields=['source_instance', 'remote_dn']),
        ]

    def __str__(self):
        return f"[{self.source_instance.name}] {self.remote_dn} → {self.dept.name}"


class UserMapping(models.Model):
    """用户映射：追踪 LDAP/AD 用户 → 本地 Users 的关联

    通过 remote_dn 定位远程用户，每次同步刷新 remote_attrs 快照。
    """
    source_instance = models.ForeignKey(
        'integration.ConnectorInstance',
        on_delete=models.CASCADE,
        related_name='user_mappings',
        verbose_name="Source Instance",
        help_text="集成中心的连接器实例 / ConnectorInstance in Integration Hub",
        db_constraint=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sync_mappings',
        verbose_name="Local User",
        help_text="本地的系统用户 / Local user record",
        db_constraint=False,
    )
    remote_dn = models.CharField(
        max_length=512,
        db_index=True,
        verbose_name="Remote DN",
        help_text="LDAP 中该用户的 Distinguished Name / LDAP DN",
    )
    remote_attrs = models.JSONField(
        default=dict,
        verbose_name="Remote Attributes",
        help_text="远端属性快照，用于 diff 对比 / Cached remote attributes for diff",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Created At",
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Updated At",
    )

    class Meta:
        db_table = _sync_table("user_mapping")
        verbose_name = "User Mapping"
        verbose_name_plural = "User Mappings"
        unique_together = [('source_instance', 'remote_dn')]
        indexes = [
            models.Index(fields=['source_instance', 'remote_dn']),
        ]

    def __str__(self):
        return f"[{self.source_instance.name}] {self.remote_dn} → {self.user.username}"
