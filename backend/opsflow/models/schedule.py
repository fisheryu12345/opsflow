from django.db import models
from django.conf import settings


class SchedulePlan(models.Model):
    """调度计划 — 一次性或周期性自动执行"""
    class ScheduleType(models.TextChoices):
        ONE_TIME = 'one_time', 'One-time'
        CRON = 'cron', 'Periodic'
        CMDB_EVENT = 'cmdb_event', 'CMDB Event'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'
        EXPIRED = 'expired', 'Expired'

    template = models.ForeignKey(
        'FlowTemplate', on_delete=models.CASCADE, related_name='schedule_plans',
        verbose_name="Template"
    )
    project = models.ForeignKey(
        'OpsProject', on_delete=models.CASCADE, null=True, blank=True,
        related_name='schedule_plans', verbose_name="Project"
    )
    name = models.CharField(max_length=128, verbose_name="Schedule Name")
    description = models.CharField(max_length=255, blank=True, verbose_name="Description")
    schedule_type = models.CharField(
        max_length=16, choices=ScheduleType.choices, verbose_name="Schedule Type"
    )
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="Scheduled At")
    cron_expr = models.CharField(max_length=64, blank=True, verbose_name="Cron Expression")
    cron_description = models.CharField(max_length=128, blank=True, verbose_name="Cron Description")
    timezone = models.CharField(max_length=32, default='Asia/Shanghai', verbose_name="Timezone")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE, verbose_name="Status"
    )
    max_retries = models.IntegerField(default=0, verbose_name="Max Retries")
    retry_delay = models.IntegerField(default=300, verbose_name="Retry Delay (s)")
    template_snapshot = models.JSONField(null=True, blank=True, verbose_name="Template Snapshot")
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Run At")
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Next Run At")
    total_run_count = models.IntegerField(default=0, verbose_name="Total Run Count")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Creator"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'opsflow_schedule_plan'
        ordering = ['-created_at']
        verbose_name = "Schedule Plan"
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'name'],
                name='uq_schedule_plan_template_name'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_schedule_type_display()})"
