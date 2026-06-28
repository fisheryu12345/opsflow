"""Membership models — BusinessMember, DeployEnvironmentPermission

BusinessMember: assigns user roles within a Business. Business Admin/Editor roles
  cascade down to all Projects under that Business (via iam.resolvers).

DeployEnvironmentPermission: explicit per-user execution permission for each
  deploy environment. NOT inherited from any role hierarchy — must be granted
  explicitly. Even Platform Admin needs this for production.
"""
from django.db import models
from django.conf import settings


class BusinessMember(models.Model):
    """Business line membership — Admin/Editor roles cascade down to all Projects"""
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        EDITOR = 'editor', 'Editor'
        VIEWER = 'viewer', 'Viewer'

    business = models.ForeignKey(
        'iam.Business', on_delete=models.CASCADE, related_name='members',
        verbose_name="Business",
        help_text="所属业务线 / Parent business"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='iam_business_members',
        verbose_name="User",
        help_text="用户 / Member user"
    )
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.EDITOR,
        verbose_name="Role",
        help_text="业务线角色 / admin=业务管理员, editor=编辑者, viewer=查看者"
    )
    joined_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Joined At",
        help_text="加入时间 / When the member joined"
    )

    class Meta:
        db_table = 'iam_business_member'
        unique_together = [('business', 'user')]
        verbose_name = "Business Member"

    def __str__(self):
        return f"{self.user} @ {self.business} ({self.role})"


class DeployEnvironmentPermission(models.Model):
    """Explicit per-user execution permission for a deploy environment

    NOT inherited from any role hierarchy. Even Platform Admin must be
    explicitly granted can_execute for production.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='iam_env_permissions',
        verbose_name="User",
        help_text="被授权的用户 / User who receives this permission"
    )
    environment = models.ForeignKey(
        'iam.DeployEnvironment', on_delete=models.CASCADE,
        verbose_name="Deploy Environment",
        help_text="目标部署环境 / Target deploy environment"
    )
    can_execute = models.BooleanField(
        default=False, verbose_name="Can Execute",
        help_text="是否可以在此环境执行操作 / Whether execution is allowed in this env"
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name='env_permissions_granted',
        verbose_name="Granted By",
        help_text="授权人 / Who granted this permission"
    )
    granted_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Granted At",
        help_text="授权时间 / When this permission was granted"
    )

    class Meta:
        db_table = 'iam_deploy_env_permission'
        unique_together = [('user', 'environment')]
        verbose_name = "Deploy Environment Permission"

    def __str__(self):
        return f"{self.user} can_execute={self.can_execute} in {self.environment}"
