# -*- coding: utf-8 -*-
"""ITSM model definitions

事件/变更/服务请求/问题工单，基于 CoreModel 基类，关联 CMDB 资产
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix

logger = logging.getLogger(__name__)


class ServiceCategory(CoreModel):
    """服务分类 — 服务目录的一级/二级分类"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_categories', verbose_name='Project',
    )
    name = models.CharField(max_length=128, verbose_name="分类名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="分类编码")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                related_name='children', verbose_name="上级分类")
    icon = models.CharField(max_length=128, null=True, blank=True, verbose_name="图标")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    default_group = models.ForeignKey(
        'itsm.SkillGroup', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="默认分派技能组",
    )
    auto_assign = models.BooleanField(default=False, verbose_name="自动分派")

    class Meta:
        db_table = table_prefix + "itsm_service_category"
        verbose_name = "服务分类"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class SlaPolicy(CoreModel):
    """SLA 策略定义"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_sla_policies', verbose_name='Project',
    )
    priority_choices = (
        ('P1', 'P1 危急'),
        ('P2', 'P2 高'),
        ('P3', 'P3 中'),
        ('P4', 'P4 低'),
    )
    name = models.CharField(max_length=128, verbose_name="策略名称")
    priority = models.CharField(max_length=8, choices=priority_choices, unique=True, verbose_name="优先级")
    response_minutes = models.IntegerField(default=60, verbose_name="响应时限(分钟)")
    resolve_minutes = models.IntegerField(default=480, verbose_name="解决时限(分钟)")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = table_prefix + "itsm_sla_policy"
        verbose_name = "SLA 策略"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name} ({self.priority})"


class Incident(CoreModel):
    """事件工单 (Incident)"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_incidents', verbose_name='Project',
    )
    incident_status_choices = (
        ('new', '新建'),
        ('assigned', '待分派'),
        ('in_progress', '处理中'),
        ('resolved', '已解决'),
        ('closed', '已关闭'),
        ('escalated', '已升级'),
    )
    source_choices = (
        ('alert', '监控告警'),
        ('user', '用户提报'),
        ('api', 'API 接入'),
    )

    incident_id = models.CharField(max_length=32, unique=True, verbose_name="工单编号")
    title = models.CharField(max_length=255, verbose_name="标题")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    status = models.CharField(max_length=32, choices=incident_status_choices, default='new', verbose_name="状态")
    priority = models.CharField(max_length=8, choices=SlaPolicy.priority_choices, default='P3', verbose_name="优先级")
    source = models.CharField(max_length=32, choices=source_choices, default='user', verbose_name="来源")
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, verbose_name="服务分类")
    assignee = models.ForeignKey('system.Users', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='incidents', verbose_name="处理人")
    sla_policy = models.ForeignKey(SlaPolicy, on_delete=models.SET_NULL, null=True, verbose_name="SLA 策略")
    sla_deadline = models.DateTimeField(null=True, blank=True, verbose_name="SLA 截止时间")
    sla_status = models.CharField(max_length=32, default='ok', verbose_name="SLA 状态")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="解决时间")
    resolution = models.TextField(null=True, blank=True, verbose_name="解决方案")

    # CMDB 关联
    cmdb_biz_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="关联业务 ID")
    cmdb_host_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="关联主机 ID")
    cmdb_data = models.JSONField(default=dict, verbose_name="资产快照")

    # 告警关联
    alert_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="关联告警 ID")
    alert_data = models.JSONField(default=dict, verbose_name="告警原始数据")

    class Meta:
        db_table = table_prefix + "itsm_incident"
        verbose_name = "事件工单"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.incident_id} - {self.title}"


class Change(CoreModel):
    """变更申请 (Change)"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_changes', verbose_name='Project',
    )
    change_type_choices = (
        ('standard', '标准变更'),
        ('normal', '普通变更'),
        ('emergency', '紧急变更'),
    )
    status_choices = (
        ('draft', '草稿'),
        ('pending_approval', '待审批'),
        ('approved', '已批准'),
        ('rejected', '已驳回'),
        ('in_progress', '执行中'),
        ('completed', '已完成'),
        ('rolled_back', '已回滚'),
        ('closed', '已关闭'),
    )

    change_id = models.CharField(max_length=32, unique=True, verbose_name="变更编号")
    title = models.CharField(max_length=255, verbose_name="标题")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    change_type = models.CharField(max_length=32, choices=change_type_choices, default='normal', verbose_name="变更类型")
    status = models.CharField(max_length=32, choices=status_choices, default='draft', verbose_name="状态")
    risk_level = models.CharField(max_length=32, default='low', verbose_name="风险等级")
    applicant = models.ForeignKey('system.Users', on_delete=models.SET_NULL, null=True,
                                   related_name='changes', verbose_name="申请人")
    assignee = models.ForeignKey('system.Users', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='change_tasks', verbose_name="执行人")
    planned_start = models.DateTimeField(null=True, blank=True, verbose_name="计划开始时间")
    planned_end = models.DateTimeField(null=True, blank=True, verbose_name="计划结束时间")
    rollback_plan = models.TextField(null=True, blank=True, verbose_name="回滚计划")
    approval_note = models.TextField(null=True, blank=True, verbose_name="审批意见")
    opsflow_execution_id = models.CharField(max_length=64, null=True, blank=True,
                                             verbose_name="关联 OpsFlow 执行 ID")
    cmdb_biz_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="关联业务 ID")

    class Meta:
        db_table = table_prefix + "itsm_change"
        verbose_name = "变更申请"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.change_id} - {self.title}"


class ServiceRequest(CoreModel):
    """服务请求 (Service Request)"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_requests', verbose_name='Project',
    )
    status_choices = (
        ('pending', '待处理'),
        ('in_progress', '处理中'),
        ('fulfilled', '已完成'),
        ('rejected', '已驳回'),
        ('cancelled', '已取消'),
    )

    request_id = models.CharField(max_length=32, unique=True, verbose_name="请求编号")
    title = models.CharField(max_length=255, verbose_name="标题")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    status = models.CharField(max_length=32, choices=status_choices, default='pending', verbose_name="状态")
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, verbose_name="服务分类")
    requester = models.ForeignKey('system.Users', on_delete=models.SET_NULL, null=True,
                                   related_name='service_requests', verbose_name="请求人")
    assignee = models.ForeignKey('system.Users', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='assigned_requests', verbose_name="处理人")
    form_data = models.JSONField(default=dict, verbose_name="表单数据")
    fulfilled_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    class Meta:
        db_table = table_prefix + "itsm_service_request"
        verbose_name = "服务请求"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.request_id} - {self.title}"


class Problem(CoreModel):
    """问题管理 (Problem)"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_problems', verbose_name='Project',
    )
    status_choices = (
        ('new', '新建'),
        ('investigating', '调查中'),
        ('root_cause_found', '已定位'),
        ('resolved', '已解决'),
        ('closed', '已关闭'),
    )

    problem_id = models.CharField(max_length=32, unique=True, verbose_name="问题编号")
    title = models.CharField(max_length=255, verbose_name="标题")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    status = models.CharField(max_length=32, choices=status_choices, default='new', verbose_name="状态")
    priority = models.CharField(max_length=8, choices=SlaPolicy.priority_choices, default='P3', verbose_name="优先级")
    root_cause = models.TextField(null=True, blank=True, verbose_name="根因")
    workaround = models.TextField(null=True, blank=True, verbose_name="规避方案")
    solution = models.TextField(null=True, blank=True, verbose_name="解决方案")
    assignee = models.ForeignKey('system.Users', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='problems', verbose_name="处理人")
    related_incidents = models.ManyToManyField(Incident, blank=True, verbose_name="关联事件")
    known_error = models.BooleanField(default=False, verbose_name="已知错误")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="解决时间")

    class Meta:
        db_table = table_prefix + "itsm_problem"
        verbose_name = "问题"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.problem_id} - {self.title}"
