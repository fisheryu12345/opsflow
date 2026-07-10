# -*- coding: utf-8 -*-
"""NotificationTemplate model for reusable notification presets."""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class NotificationTemplate(CoreModel):
    """通知模板 — 预设标题/正文/渠道/接收人，触发器选择即可复用"""

    CHANNEL_CHOICES = (
        ('site', '站内信'),
        ('wecom', '企业微信'),
        ('dingtalk', '钉钉'),
        ('email', '邮件'),
    )

    RECEIVER_CHOICES = (
        ('processor', '处理人'),
        ('starter', '提单人'),
        ('leader', '组长'),
    )

    name = models.CharField(max_length=128, verbose_name="模板名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="模板名称(英文)")
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_notification_templates', verbose_name='Project',
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    channels = models.JSONField(default=list, verbose_name="通知渠道")
    title_tpl = models.CharField(max_length=500, blank=True, default='', verbose_name="标题模板")
    body_tpl = models.TextField(blank=True, default='', verbose_name="正文模板")
    receivers = models.JSONField(default=list, verbose_name="接收人")

    class Meta:
        db_table = table_prefix + "itsm_notification_template"
        verbose_name = "通知模板"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def display_name(self, lang='zh'):
        return self.name_en if lang == 'en' and self.name_en else self.name
