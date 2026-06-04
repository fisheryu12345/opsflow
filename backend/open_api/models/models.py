"""Open API Gateway models — third-party app management, tokens, webhook subscriptions

开放 API：第三方应用管理、访问凭证、Webhook 事件订阅
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)


class ApiApp(CoreModel):
    """第三方应用"""
    status_choices = (
        ('active', '活跃'),
        ('disabled', '已禁用'),
        ('expired', '已过期'),
    )

    name = models.CharField(max_length=255, verbose_name="应用名称")
    company = models.CharField(max_length=255, null=True, blank=True, verbose_name="所属公司")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    contact_name = models.CharField(max_length=128, null=True, blank=True, verbose_name="联系人")
    contact_email = models.EmailField(null=True, blank=True, verbose_name="联系邮箱")
    status = models.CharField(max_length=32, choices=status_choices, default='active', verbose_name="状态")
    rate_limit = models.IntegerField(default=100, verbose_name="频率限制(QPS)", help_text="每秒请求数")
    allowed_apis = models.JSONField(default=list, verbose_name="允许的 API 列表",
                                     help_text="API 路径前缀列表，空表示全部允许")
    allowed_ips = models.JSONField(default=list, verbose_name="IP 白名单")
    expire_at = models.DateTimeField(null=True, blank=True, verbose_name="过期时间")

    class Meta:
        db_table = table_prefix + "open_api_app"
        verbose_name = "第三方应用"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.name} ({self.company or 'N/A'})"


class OpenApiToken(CoreModel):
    """应用访问凭证"""
    token_status_choices = (
        ('active', '有效'),
        ('revoked', '已吊销'),
        ('expired', '已过期'),
    )

    app = models.ForeignKey(ApiApp, on_delete=models.CASCADE, related_name='tokens', verbose_name="所属应用")
    access_key = models.CharField(max_length=64, unique=True, verbose_name="Access Key")
    secret_key = models.CharField(max_length=128, verbose_name="Secret Key (加密存储)")
    status = models.CharField(max_length=32, choices=token_status_choices, default='active', verbose_name="状态")
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name="最后使用时间")
    expire_at = models.DateTimeField(null=True, blank=True, verbose_name="过期时间")
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name="描述")

    class Meta:
        db_table = table_prefix + "open_api_token"
        verbose_name = "API 凭证"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.access_key} ({self.app.name})"


class WebhookSubscription(CoreModel):
    """事件订阅 — 第三方系统通过 Webhook 接收平台事件"""
    event_type_choices = (
        ('incident.created', '事件工单创建'),
        ('incident.updated', '事件工单更新'),
        ('incident.resolved', '事件工单解决'),
        ('alert.firing', '告警触发'),
        ('alert.resolved', '告警恢复'),
        ('job.completed', '作业完成'),
        ('execution.completed', '流程完成'),
    )

    app = models.ForeignKey(ApiApp, on_delete=models.CASCADE, related_name='webhooks', verbose_name="所属应用")
    name = models.CharField(max_length=255, verbose_name="订阅名称")
    event_type = models.CharField(max_length=128, choices=event_type_choices, verbose_name="事件类型")
    callback_url = models.URLField(max_length=1024, verbose_name="回调地址")
    secret = models.CharField(max_length=255, null=True, blank=True, verbose_name="签名密钥",
                               help_text="用于 HMAC 签名验证")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    retry_count = models.IntegerField(default=3, verbose_name="重试次数")
    retry_interval = models.IntegerField(default=60, verbose_name="重试间隔(秒)")
    last_delivery_at = models.DateTimeField(null=True, blank=True, verbose_name="最后投递时间")
    last_delivery_status = models.CharField(max_length=32, default='pending', verbose_name="最后投递状态")

    class Meta:
        db_table = table_prefix + "open_api_webhook"
        verbose_name = "事件订阅"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.name} ({self.event_type})"


class OpenApiLog(CoreModel):
    """API 调用日志"""
    app = models.ForeignKey(ApiApp, on_delete=models.SET_NULL, null=True, related_name='api_logs', verbose_name="调用应用")
    token = models.ForeignKey(OpenApiToken, on_delete=models.SET_NULL, null=True, verbose_name="使用凭证")
    request_path = models.CharField(max_length=512, verbose_name="请求路径")
    request_method = models.CharField(max_length=16, verbose_name="请求方法")
    request_params = models.JSONField(default=dict, verbose_name="请求参数")
    response_status = models.IntegerField(default=200, verbose_name="响应状态码")
    duration_ms = models.IntegerField(default=0, verbose_name="耗时(ms)")
    ip_address = models.CharField(max_length=64, null=True, blank=True, verbose_name="请求 IP")
    user_agent = models.CharField(max_length=512, null=True, blank=True, verbose_name="User-Agent")
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")

    class Meta:
        db_table = table_prefix + "open_api_log"
        verbose_name = "API 调用日志"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.request_method} {self.request_path}"
