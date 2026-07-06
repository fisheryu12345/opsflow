# -*- coding: utf-8 -*-
"""ServiceItem model — 服务目录的核心实体"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


class ServiceItem(CoreModel):
    """服务项 — 服务目录的核心实体"""
    MODE_CHOICES = (
        ('flow', '流程驱动'),
        ('lightweight', '快捷服务'),
    )
    VISIBILITY_CHOICES = (
        ('all', '全员'),
        ('role', '指定角色'),
        ('user', '指定用户'),
    )
    name = models.CharField(max_length=128, verbose_name="服务名称")
    name_en = models.CharField(max_length=128, blank=True, default='', verbose_name="服务名称(英文)")
    description = models.TextField(blank=True, default='', verbose_name="服务描述")
    description_en = models.TextField(blank=True, default='', verbose_name="服务描述(英文)")
    icon = models.CharField(max_length=64, null=True, blank=True, verbose_name="图标 emoji")
    cover_image = models.CharField(max_length=256, null=True, blank=True, verbose_name="封面图 URL")

    # 归属分类
    category = models.ForeignKey(
        'itsm.ServiceCategory', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='service_items', verbose_name="服务分类",
    )

    # 模式与流程绑定
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default='flow', verbose_name="服务模式")
    workflow = models.ForeignKey(
        'itsm.Workflow', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="绑定流程（流程驱动模式必选）",
    )

    # 表单字段（可选，不配置则使用 Workflow 默认字段）
    form_fields = models.JSONField(default=list, verbose_name="自定义表单字段定义")

    # SLA
    sla_policy = models.ForeignKey(
        'itsm.SlaPolicy', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="SLA 策略",
    )

    # 可见性控制
    visible_to = models.CharField(
        max_length=64, default='all', choices=VISIBILITY_CHOICES,
        verbose_name="可见范围",
    )
    visible_roles = models.JSONField(default=list, verbose_name="可见角色列表")
    visible_users = models.JSONField(default=list, verbose_name="可见用户列表")

    # 快捷服务配置
    default_assignee_type = models.CharField(
        max_length=32, blank=True, default='', verbose_name="快捷服务分派方式",
    )
    default_assignee = models.CharField(
        max_length=128, blank=True, default='', verbose_name="快捷服务默认处理人",
    )

    # 展示信息
    expected_duration = models.CharField(max_length=64, blank=True, default='', verbose_name="预计时长")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    # 多租户
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_service_items', verbose_name='Project',
    )

    class Meta:
        db_table = table_prefix + "itsm_service_item"
        verbose_name = "服务项"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def display_name(self, lang='zh'):
        return self.name_en if lang == 'en' and self.name_en else self.name

    def display_description(self, lang='zh'):
        return self.description_en if lang == 'en' and self.description_en else self.description
