"""Unified RBAC models — replaces dvadmin Role/MenuButton/RoleMenuPermission

Migration target: all permission management moves to these 4 models.
Menu retains navigation structure only (permission semantics removed).
"""
from django.conf import settings
from django.db import models

from django.conf import settings
from common.utils.models import CoreModel, table_prefix


class IAMPermission(CoreModel):
    """Unique permission definition — replaces MenuButton"""
    codename = models.CharField(unique=True, max_length=128, verbose_name="权限标识")
    label = models.CharField(max_length=128, verbose_name="权限名称")
    app = models.CharField(max_length=64, verbose_name="所属应用",
                            help_text="system / opsflow / itsm / cmdb / monitor / integration / portal")
    scope = models.CharField(max_length=8, choices=[
        ('platform', '平台级'),
        ('project', '项目级'),
    ], default='platform', verbose_name="作用域")

    class Meta:
        db_table = table_prefix + 'iam_permission'
        verbose_name = "权限定义"
        verbose_name_plural = verbose_name
        ordering = ['app', 'codename']

    def __str__(self):
        return f"{self.codename} ({self.get_scope_display()})"


class IAMRole(CoreModel):
    """Unified role — replaces dvadmin Role, pure permission set"""
    name = models.CharField(max_length=64, verbose_name="角色名称")
    key = models.CharField(unique=True, max_length=64, verbose_name="角色标识")
    is_system = models.BooleanField(default=False, verbose_name="系统预置")

    class Meta:
        db_table = table_prefix + 'iam_role_new'
        verbose_name = "统一角色"
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


class IAMRolePermission(CoreModel):
    """Role-Permission binding — replaces RoleMenuButtonPermission"""
    role = models.ForeignKey(IAMRole, on_delete=models.CASCADE, related_name='role_permissions', verbose_name="角色")
    permission = models.ForeignKey(IAMPermission, on_delete=models.CASCADE, related_name='role_permissions', verbose_name="权限")
    min_project_role = models.CharField(
        max_length=16, null=True, blank=True,
        choices=[('viewer', 'Viewer'), ('editor', 'Editor'), ('admin', 'Admin')],
        verbose_name="最低项目角色",
        help_text="仅 project 作用域有效。用户在该项目中的角色 >= 此值才有权限。"
    )

    class Meta:
        db_table = table_prefix + 'iam_role_permission'
        verbose_name = "角色权限关联"
        verbose_name_plural = verbose_name
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role} - {self.permission}"


class IAMUserRole(CoreModel):
    """User-Role binding — replaces user.role M2M"""
    user = models.IntegerField(null=True, blank=True, verbose_name="用户", db_column='user_id')
    role = models.ForeignKey(IAMRole, on_delete=models.CASCADE, related_name='user_roles', verbose_name="角色")

    class Meta:
        db_table = table_prefix + 'iam_user_role'
        verbose_name = "用户角色分配"
        verbose_name_plural = verbose_name
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user} - {self.role}"
