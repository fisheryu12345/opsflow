from django.db import models
from django.conf import settings


class OperationRecord(models.Model):
    """操作审计记录 — 记录所有重要用户操作"""
    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        PUBLISH = 'publish', 'Publish'
        ROLLBACK = 'rollback', 'Rollback'
        EXECUTE = 'execute', 'Execute'
        APPROVE = 'approve', 'Approve'
        REJECT = 'reject', 'Reject'

    action = models.CharField(max_length=16, choices=Action.choices, verbose_name='Action')
    resource_type = models.CharField(max_length=32, verbose_name='Resource Type')
    resource_id = models.CharField(max_length=32, blank=True, verbose_name='Resource ID')
    resource_name = models.CharField(max_length=200, blank=True, verbose_name='Resource Name')
    detail = models.JSONField(default=dict, verbose_name='Detail')
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Operator'
    )
    business = models.ForeignKey(
        'iam.Business', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Business',
        help_text='Business for scoping audit visibility / 审计记录归属业务线'
    )
    project = models.ForeignKey(
        'iam.Project', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Project',
        help_text='Project for scoping audit visibility / 审计记录归属项目'
    )
    ip_address = models.CharField(max_length=45, blank=True, verbose_name='IP Address')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_operation_record'
        ordering = ['-created_at']
        verbose_name = 'Operation Record'

    def __str__(self):
        return f'{self.action} {self.resource_type}[{self.resource_id}]'


class OpsLog(models.Model):
    """审计日志 — 每一步的详细执行记录"""
    execution = models.ForeignKey(
        'FlowExecution', on_delete=models.CASCADE, related_name='logs',
        verbose_name="Execution"
    )
    step = models.CharField(max_length=200, blank=True, verbose_name="Step ID")
    command = models.TextField(blank=True, verbose_name="Command")
    stdout = models.TextField(blank=True, verbose_name="Stdout")
    stderr = models.TextField(blank=True, verbose_name="Stderr")
    returncode = models.IntegerField(null=True, blank=True, verbose_name="Return Code")
    risk_level = models.CharField(
        max_length=16,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        default='low', verbose_name="Risk Level"
    )
    approved_by = models.CharField(max_length=128, blank=True, verbose_name="Approved By")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_log'
        ordering = ['created_at']
        verbose_name = "Audit Log"

    def __str__(self):
        return f"[{self.step}] rc={self.returncode}"
