"""Project model — migrated from opsflow.models.project

OpsProject → Project (renamed, moved from opsflow app to iam app).
ProjectMember also migrated here, role choices preserved.
"""
from django.db import models
from django.conf import settings


class Project(models.Model):
    """Ops workspace — the operational unit for workflow management

    Migrated from opsflow.OpsProject. Now owned by iam app as cross-cutting
    infrastructure that all sub-products reference.
    """
    name = models.CharField(
        max_length=128, unique=True, verbose_name="Name",
        help_text="项目名称 / Project name"
    )
    description = models.CharField(
        max_length=255, blank=True, verbose_name="Description",
        help_text="项目描述 / Project description"
    )
    business = models.ForeignKey(
        'iam.Business', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='projects',
        verbose_name="Business",
        help_text="所属业务线 / Parent business line. null for backward compatibility."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Owner",
        help_text="项目负责人 / Project owner"
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Is Active",
        help_text="是否启用 / Whether this project is active"
    )
    max_schedule_plans = models.IntegerField(
        default=20, verbose_name="Max Schedule Plans",
        help_text="Maximum schedule plans per project, 0=unlimited / 项目最多定时任务数，0=不限制"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Updated At"
    )

    class Meta:
        db_table = 'iam_project'
        ordering = ['name']
        verbose_name = "Project"

    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    """Project membership — which users belong to which projects

    Migrated from opsflow.ProjectMember. Role choices preserved: admin/editor/viewer.
    BusinessAdmin inherits equivalent Project Admin access automatically
    (handled at resolver level, not enforced via ProjectMember records).
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        EDITOR = 'editor', 'Editor'
        VIEWER = 'viewer', 'Viewer'

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='members',
        verbose_name="Project",
        help_text="所属项目 / Parent project"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='iam_project_members',
        verbose_name="User",
        help_text="用户 / Member user"
    )
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.EDITOR,
        verbose_name="Role",
        help_text="项目角色 / admin=管理员, editor=编辑者, viewer=查看者"
    )
    joined_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Joined At",
        help_text="加入时间 / When the member joined"
    )

    class Meta:
        db_table = 'iam_project_member'
        unique_together = [('project', 'user')]
        verbose_name = "Project Member"

    def __str__(self):
        return f"{self.user} @ {self.project} ({self.role})"
