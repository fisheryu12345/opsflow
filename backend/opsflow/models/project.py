from django.db import models
from django.conf import settings


class OpsProject(models.Model):
    """OpsFlow 项目 — 数据隔离单元"""
    name = models.CharField(max_length=128, unique=True, verbose_name="Project Name")
    description = models.CharField(max_length=255, blank=True, verbose_name="Description")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Owner"
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    max_schedule_plans = models.IntegerField(
        default=20, verbose_name="Max Schedule Plans",
        help_text="项目最多可创建的定时任务数，0=不限制"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_project'
        ordering = ['name']
        verbose_name = "OpsFlow Project"

    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    """项目成员 — 记录哪些用户属于哪些项目"""
    class Role(models.TextChoices):
        ADMIN = 'admin', '管理员'
        EDITOR = 'editor', '编辑者'
        VIEWER = 'viewer', '查看者'

    project = models.ForeignKey(
        OpsProject, on_delete=models.CASCADE, related_name='members',
        verbose_name="Project"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name="User"
    )
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.EDITOR,
        verbose_name="Role"
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="Joined At")

    class Meta:
        db_table = 'ops_project_member'
        unique_together = [('project', 'user')]
        verbose_name = "Project Member"

    def __str__(self):
        return f"{self.user} @ {self.project} ({self.role})"
