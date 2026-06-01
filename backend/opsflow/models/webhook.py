from django.db import models
from django.conf import settings


class WebhookConfig(models.Model):
    """Webhook 回调配置 — 绑定到模板，执行完成后触发"""
    template = models.ForeignKey(
        'FlowTemplate', on_delete=models.CASCADE, related_name='webhooks',
        verbose_name="Template"
    )
    name = models.CharField(max_length=128, verbose_name="Webhook Name")
    url = models.URLField(max_length=1024, verbose_name="Callback URL")
    secret = models.CharField(max_length=256, blank=True, verbose_name="HMAC Secret",
                               help_text="HMAC 签名密钥（可选）")
    trigger_events = models.JSONField(
        default=list, blank=True, verbose_name="Trigger Events",
        help_text="['completed', 'failed'] 触发事件列表"
    )
    retry_count = models.IntegerField(default=3, verbose_name="Max Retries")
    retry_interval = models.IntegerField(default=10, verbose_name="Retry Interval (s)")
    enabled = models.BooleanField(default=True, verbose_name="Enabled")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Creator"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_webhook_config'
        ordering = ['-created_at']
        verbose_name = "Webhook Config"

    def __str__(self):
        return f"{self.name} → {self.url}"


class WebhookLog(models.Model):
    """Webhook 投递日志"""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    webhook = models.ForeignKey(
        WebhookConfig, on_delete=models.CASCADE, related_name='logs',
        verbose_name="Webhook Config"
    )
    execution = models.ForeignKey(
        'FlowExecution', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='webhook_logs', verbose_name="Execution"
    )
    event = models.CharField(max_length=32, verbose_name="Event Type")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
        verbose_name="Status"
    )
    request_url = models.URLField(max_length=1024, verbose_name="Request URL")
    request_body = models.JSONField(default=dict, verbose_name="Request Body")
    response_status = models.IntegerField(null=True, blank=True, verbose_name="Response Status")
    response_body = models.TextField(blank=True, verbose_name="Response Body")
    retry_count = models.IntegerField(default=0, verbose_name="Retry Count")
    error_message = models.TextField(blank=True, verbose_name="Error Message")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_webhook_log'
        ordering = ['-created_at']
        verbose_name = "Webhook Log"

    def __str__(self):
        return f"[{self.webhook_id}] {self.event} → {self.status}"
